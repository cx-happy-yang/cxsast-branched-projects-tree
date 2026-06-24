"""Create ~3011 projects using branches (which don't consume license)."""
import os, sys, random, time

sys.path.insert(0, r'E:\github.com\checkmarx-python-sdk')
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

from CheckmarxPythonSDK.api_client import ApiClient
from CheckmarxPythonSDK.configuration import Configuration
from CheckmarxPythonSDK.CxRestAPISDK import ProjectsAPI, TeamAPI

base_url = os.getenv('CXSAST_BASE_URL', '').rstrip('/')
v = os.getenv('CXSAST_VERIFY', 'True').strip()
verify = False if v.lower() in ('false', '0', 'no', 'off') else True

config = Configuration(
    server_base_url=base_url,
    token_url=f'{base_url}/cxrestapi/auth/identity/connect/token',
    username=os.getenv('CXSAST_USERNAME'),
    password=os.getenv('CXSAST_PASSWORD'),
    grant_type=os.getenv('CXSAST_GRANT_TYPE', 'password'),
    scope=os.getenv('CXSAST_SCOPE', 'sast_rest_api'),
    client_id=os.getenv('CXSAST_CLIENT_ID', 'resource_owner_client'),
    client_secret=os.getenv('CXSAST_CLIENT_SECRET'),
    verify=verify, timeout=120, max_retries=3,
)

api_client = ApiClient(configuration=config)
projects_api = ProjectsAPI(api_client=api_client)
team_api = TeamAPI(api_client=api_client)

teams = team_api.get_all_teams()
team_ids = [t.team_id for t in teams]
print(f'Using {len(team_ids)} teams')

BATCH = 80   # under 100/min
COOLDOWN = 62

cn_prefixes = [
    '同享超级智能体', '天骄学堂家长', '渠道企业信息', '业务层',
    '数据平台', '用户中心', '订单管理', '支付网关', '消息推送',
    '报表分析', '权限管理', '配置中心', '日志采集', '监控告警',
    '自动化测试', '性能压测', '安全扫描', '代码审查', '持续集成', '发布管理',
]
eng_prefixes = [
    'service', 'api', 'backend', 'frontend', 'mobile', 'data-pipeline',
    'auth', 'payment', 'notification', 'analytics', 'reporting', 'admin',
    'core', 'shared', 'common', 'utils', 'infra', 'deploy', 'monitor', 'test',
]

def make_name(prefix=''):
    if random.random() < 0.4:
        cn = random.choice(cn_prefixes)
        return f'{prefix}{cn}-{random.randint(100,999)}'
    return f'{prefix}{random.choice(eng_prefixes)}-{random.randint(1000,99999)}'

existing = projects_api.get_all_project_details()
current_total = len(existing)
target_total = 3011
print(f'Current total: {current_total}, target: {target_total}')
print(f'License-used roots: {sum(1 for p in existing if not p.original_project_id or p.original_project_id == "")}')

# Find all root projects (potential parents for branching)
roots = [p.project_id for p in existing if not p.original_project_id or p.original_project_id == '']
print(f'Root projects available for branching: {len(roots)}')

start = time.time()
total_created = 0
errors = 0
batch_count = 0

# Phase 1: Create branches off existing roots in bulk
needed = target_total - current_total
print(f'\nNeed {needed} more projects via branching...')

# Build a pool of parent IDs, replenishing as we create new branches
parent_pool = list(roots)
all_p = existing
pid_map = {p.project_id: p for p in all_p}

while total_created < needed:
    if not parent_pool:
        # Refresh parent pool from the API
        all_p = projects_api.get_all_project_details()
        parent_pool = [p.project_id for p in all_p]
        pid_map = {p.project_id: p for p in all_p}
        print(f'\nRefreshed pool: {len(parent_pool)} potential parents')

    # Pick parents randomly, but prefer ones with fewer children
    random.shuffle(parent_pool)
    chunk = parent_pool[:min(BATCH, len(parent_pool))]
    parent_pool = parent_pool[min(BATCH, len(parent_pool)):]

    for parent_id in chunk:
        if total_created >= needed:
            break

        # Create 1-5 children per parent
        n_children = min(random.randint(1, 5), needed - total_created)
        for _ in range(n_children):
            name = make_name()
            depth_tag = 'leaf' if random.random() < 0.7 else ''
            if depth_tag:
                name = name  # mark as leaf later

            for attempt in range(3):
                try:
                    resp = projects_api.create_branched_project(parent_id, name)
                    total_created += 1
                    # Add new project to parent pool for deeper branching
                    parent_pool.append(resp.id)
                    break
                except Exception as exc:
                    err = str(exc)
                    if '429' in err or 'quota' in err.lower():
                        time.sleep(5)
                    else:
                        errors += 1
                        break

        batch_count += 1

    elapsed = time.time() - start
    remaining = needed - total_created
    if total_created > 0:
        rate = total_created / elapsed * 60
        eta = remaining / (total_created / elapsed)
        pct = (current_total + total_created) * 100 // target_total
        print(f'  [{current_total+total_created}/{target_total}] {pct}% | {rate:.0f}/min | ETA {eta:.0f}s | pool:{len(parent_pool)} | err:{errors}', flush=True)

    if total_created < needed:
        time.sleep(COOLDOWN)

elapsed = time.time() - start
print(f'\nDone in {elapsed:.0f}s! Created {total_created} branches, {errors} errors')

# Summary
all_p = projects_api.get_all_project_details()
print(f'Total projects: {len(all_p)}')
children = {}
for p in all_p:
    pid = p.original_project_id
    if pid and pid != '':
        children.setdefault(int(pid), []).append(p.project_id)
max_depth = 0
def depth(pid, d=0):
    global max_depth
    max_depth = max(max_depth, d)
    for cid in children.get(pid, []):
        depth(cid, d+1)
for p in all_p:
    if not p.original_project_id or p.original_project_id == '':
        depth(p.project_id)
print(f'Max tree depth: {max_depth}')
print(f'Projects with branches: {len(children)}')
