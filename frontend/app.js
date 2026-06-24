(function () {
  'use strict';

  // -----------------------------------------------------------------------
  // State
  // -----------------------------------------------------------------------
  const state = {
    treeData: null,
    selectedIds: new Set(),
    expandedIds: new Set(),
    flatNodeMap: new Map(),
  };

  // -----------------------------------------------------------------------
  // DOM refs
  // -----------------------------------------------------------------------
  const $loading = document.getElementById('loading');
  const $empty = document.getElementById('empty-state');
  const $treeContent = document.getElementById('tree-content');
  const $serverInd = document.getElementById('server-indicator');
  const $projectCount = document.getElementById('project-count');
  const $selectedCount = document.getElementById('selected-count');
  const $btnDelete = document.getElementById('btn-delete-selected');
  const $btnRefresh = document.getElementById('btn-refresh');
  const $btnExpandAll = document.getElementById('btn-expand-all');
  const $btnCollapseAll = document.getElementById('btn-collapse-all');
  const $filterInput = document.getElementById('filter-input');
  const $chkBranchedOnly = document.getElementById('chk-show-branched-only');
  const $notification = document.getElementById('notification');
  const $modalOverlay = document.getElementById('modal-overlay');
  const $modalList = document.getElementById('modal-project-list');
  const $modalClose = document.getElementById('modal-close');
  const $modalCancel = document.getElementById('modal-cancel');
  const $modalConfirm = document.getElementById('modal-confirm');

  // -----------------------------------------------------------------------
  // Notification
  // -----------------------------------------------------------------------
  let notifyTimer = null;
  function notify(msg, type) {
    $notification.textContent = msg;
    $notification.className = 'notification ' + (type || 'info');
    if (notifyTimer) clearTimeout(notifyTimer);
    notifyTimer = setTimeout(function () {
      $notification.classList.add('hidden');
    }, 4000);
  }

  // -----------------------------------------------------------------------
  // API helpers
  // -----------------------------------------------------------------------
  async function apiFetch(url, opts) {
    var resp = await fetch(url, opts);
    if (!resp.ok) {
      var body = await resp.json().catch(function () { return {}; });
      throw new Error(body.error || body.message || 'HTTP ' + resp.status);
    }
    return resp.json();
  }

  function setLoading(on) {
    if (on) {
      $loading.classList.remove('hidden');
      $empty.classList.add('hidden');
      $treeContent.innerHTML = '';
    } else {
      $loading.classList.add('hidden');
    }
  }

  // -----------------------------------------------------------------------
  // Health check
  // -----------------------------------------------------------------------
  function checkHealth() {
    $serverInd.className = 'server-indicator checking';
    $serverInd.title = 'Checking server...';

    apiFetch('/api/health')
      .then(function (data) {
        $serverInd.className = 'server-indicator online';
        $serverInd.title = 'Connected to ' + data.server + ' (' + data.project_count + ' projects)';
      })
      .catch(function () {
        $serverInd.className = 'server-indicator offline';
        $serverInd.title = 'Cannot connect to CxSAST';
      });
  }

  // -----------------------------------------------------------------------
  // Tree rendering
  // -----------------------------------------------------------------------
  function renderTree() {
    $treeContent.innerHTML = '';

    if (!state.treeData || !state.treeData.projects || state.treeData.projects.length === 0) {
      $empty.classList.remove('hidden');
      $projectCount.textContent = '0 projects';
      return;
    }

    $empty.classList.add('hidden');
    $projectCount.textContent = state.treeData.total_projects + ' projects';

    var frag = document.createDocumentFragment();
    state.treeData.projects.forEach(function (node) {
      frag.appendChild(renderNode(node, 0));
    });
    $treeContent.appendChild(frag);
  }

  function renderNode(node, level) {
    var li = document.createElement('li');
    li.className = 'tree-node';
    li.dataset.projectId = node.project_id;

    var row = document.createElement('div');
    row.className = 'node-row';

    // Toggle button
    var toggle = document.createElement('button');
    toggle.className = 'toggle-btn' + (node.children.length > 0 ? '' : ' empty');
    toggle.innerHTML = '&#9654;';
    toggle.title = node.children.length + ' child(ren)';
    if (state.expandedIds.has(node.project_id)) {
      toggle.classList.add('expanded');
    }
    toggle.addEventListener('click', function (e) {
      e.stopPropagation();
      toggleNode(node.project_id, li);
    });
    row.appendChild(toggle);

    // Checkbox — all nodes are enabled; parent selection cascades to descendants
    var cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.className = 'node-checkbox';
    cb.checked = state.selectedIds.has(node.project_id);
    cb.indeterminate = isIndeterminate(node);
    cb.title = node.is_leaf ? 'Select for deletion' : 'Select this and all ' + countDescendants(node) + ' descendants for deletion';
    cb.addEventListener('change', function () {
      setNodeChecked(node, cb.checked);
      refreshAllCheckboxes();
    });
    row.appendChild(cb);

    // Label
    var label = document.createElement('div');
    label.className = 'node-label';

    var nameSpan = document.createElement('span');
    nameSpan.className = 'node-name';
    nameSpan.textContent = node.name;
    label.appendChild(nameSpan);

    var idSpan = document.createElement('span');
    idSpan.className = 'node-id';
    idSpan.textContent = '#' + node.project_id;
    label.appendChild(idSpan);

    // Badges
    if (node.is_deprecated) {
      var depBadge = document.createElement('span');
      depBadge.className = 'badge badge-deprecated';
      depBadge.textContent = 'Deprecated';
      label.appendChild(depBadge);
    }
    if (node.is_branched) {
      var brBadge = document.createElement('span');
      brBadge.className = 'badge badge-branched';
      brBadge.textContent = 'Branched';
      label.appendChild(brBadge);
    } else if (node.child_count > 0) {
      var origBadge = document.createElement('span');
      origBadge.className = 'badge badge-original';
      origBadge.textContent = 'Original';
      label.appendChild(origBadge);
    } else {
      var soloBadge = document.createElement('span');
      soloBadge.className = 'badge badge-standalone';
      soloBadge.textContent = 'Standalone';
      label.appendChild(soloBadge);
    }

    if (node.child_count > 0) {
      var hint = document.createElement('span');
      hint.className = 'child-hint';
      hint.textContent = '(' + node.child_count + ' children)';
      label.appendChild(hint);
    }

    if (node.team_name) {
      var teamSpan = document.createElement('span');
      teamSpan.className = 'node-team';
      teamSpan.textContent = node.team_name;
      label.appendChild(teamSpan);
    }

    row.appendChild(label);

    // Single delete button — works for any node (cascades to descendants)
    var delBtn = document.createElement('button');
    delBtn.className = 'delete-single';
    delBtn.textContent = '✕';
    delBtn.title = node.is_leaf ? 'Delete this project' : 'Delete this project and all ' + countDescendants(node) + ' descendants';
    delBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      var targets = collectLeafNodes(node);
      if (targets.length > 0) confirmAndDelete(targets);
    });
    row.appendChild(delBtn);

    // Row click: toggle selection for this node and all descendants.
    // Skip if checkbox itself was clicked (native toggle + change handler handles it).
    row.addEventListener('click', function (e) {
      if (e.target && e.target.tagName === 'INPUT' && e.target.type === 'checkbox') {
        return;
      }
      var newChecked = !cb.checked;
      setNodeChecked(node, newChecked);
      refreshAllCheckboxes();
    });

    li.appendChild(row);

    // Children
    if (node.children.length > 0) {
      var childUl = document.createElement('ul');
      childUl.className = 'tree-children';
      if (!state.expandedIds.has(node.project_id)) {
        childUl.classList.add('collapsed');
      }
      node.children.forEach(function (child) {
        childUl.appendChild(renderNode(child, level + 1));
      });
      li.appendChild(childUl);
    }

    state.flatNodeMap.set(node.project_id, node);
    return li;
  }

  function toggleNode(projectId, li) {
    var children = li.querySelector(':scope > .tree-children');
    if (!children) return;

    var toggle = li.querySelector(':scope > .node-row .toggle-btn');
    var collapsed = children.classList.toggle('collapsed');

    if (collapsed) {
      state.expandedIds.delete(projectId);
      if (toggle) toggle.classList.remove('expanded');
    } else {
      state.expandedIds.add(projectId);
      if (toggle) toggle.classList.add('expanded');
    }
  }

  function expandAll() {
    state.treeData.projects.forEach(function (node) {
      expandAllRecursive(node);
    });
    renderTree();
  }

  function expandAllRecursive(node) {
    if (node.children.length > 0) {
      state.expandedIds.add(node.project_id);
      node.children.forEach(expandAllRecursive);
    }
  }

  function collapseAll() {
    state.expandedIds.clear();
    renderTree();
  }

  // -----------------------------------------------------------------------
  // Selection (cascade)
  // -----------------------------------------------------------------------

  function collectDescendantIds(node) {
    var ids = [];
    node.children.forEach(function (child) {
      ids.push(child.project_id);
      ids = ids.concat(collectDescendantIds(child));
    });
    return ids;
  }

  function countDescendants(node) {
    var count = 0;
    node.children.forEach(function (child) {
      count += 1 + countDescendants(child);
    });
    return count;
  }

  function collectLeafNodes(node) {
    if (node.is_leaf) {
      return [node];
    }
    var leaves = [];
    node.children.forEach(function (child) {
      leaves = leaves.concat(collectLeafNodes(child));
    });
    return leaves;
  }

  function setNodeChecked(node, checked) {
    if (checked) {
      state.selectedIds.add(node.project_id);
    } else {
      state.selectedIds.delete(node.project_id);
    }
    node.children.forEach(function (child) {
      setNodeChecked(child, checked);
    });
  }

  function isIndeterminate(node) {
    if (node.is_leaf) return false;
    if (state.selectedIds.has(node.project_id)) return false;
    var allDescendants = collectDescendantIds(node);
    if (allDescendants.length === 0) return false;
    var some = allDescendants.some(function (id) { return state.selectedIds.has(id); });
    return some;
  }

  function refreshAllCheckboxes() {
    var checkboxes = document.querySelectorAll('.node-checkbox');
    for (var i = 0; i < checkboxes.length; i++) {
      var cb = checkboxes[i];
      var li = cb.closest('.tree-node');
      if (!li) continue;
      var pid = parseInt(li.dataset.projectId, 10);
      var node = state.flatNodeMap.get(pid);
      if (!node) continue;
      cb.checked = state.selectedIds.has(node.project_id);
      cb.indeterminate = isIndeterminate(node);
    }
    updateSelectionUI();
  }

  function getSelectedLeafNodes() {
    var result = [];
    state.selectedIds.forEach(function (id) {
      var node = state.flatNodeMap.get(id);
      if (node && node.is_leaf) result.push(node);
    });
    return result;
  }

  function updateSelectionUI() {
    var leafCount = getSelectedLeafNodes().length;
    $selectedCount.textContent = leafCount;
    $btnDelete.disabled = leafCount === 0;
  }

  function clearSelection() {
    state.selectedIds.clear();
    updateSelectionUI();
  }

  // -----------------------------------------------------------------------
  // Delete flow
  // -----------------------------------------------------------------------
  function confirmAndDelete(nodes) {
    var list = nodes || getSelectedNodesForDisplay();
    if (list.length === 0) {
      notify('No projects selected for deletion.', 'info');
      return;
    }

    var leafIds = collectLeavesFromNodes(list).map(function (n) { return n.project_id; });

    $modalList.innerHTML = list.map(function (n) {
      var label = n.is_leaf ? '' : ' <span style="color:#636e72;font-size:0.8rem">(including ' + countDescendants(n) + ' descendant' + (countDescendants(n) !== 1 ? 's' : '') + ')</span>';
      return '<div class="modal-item">#' + n.project_id + ' &mdash; ' + escapeHtml(n.name) + label + '</div>';
    }).join('');
    $modalOverlay.classList.remove('hidden');

    $modalConfirm.onclick = function () {
      executeBatchDelete(leafIds);
      $modalOverlay.classList.add('hidden');
    };
  }

  function getSelectedNodesForDisplay() {
    // Return only the topmost selected nodes — if a parent is selected,
    // don't also list its already-selected children separately.
    var result = [];
    state.selectedIds.forEach(function (id) {
      var node = state.flatNodeMap.get(id);
      if (!node) return;
      // Omit if this node's parent is also selected
      if (node.original_project_id && state.selectedIds.has(parseInt(node.original_project_id, 10))) {
        return;
      }
      result.push(node);
    });
    result.sort(function (a, b) { return (a.name || '').localeCompare(b.name || ''); });
    return result;
  }

  function collectLeavesFromNodes(nodes) {
    var leaves = [];
    nodes.forEach(function (n) {
      leaves = leaves.concat(collectLeafNodes(n));
    });
    // Deduplicate
    var seen = new Set();
    return leaves.filter(function (n) {
      if (seen.has(n.project_id)) return false;
      seen.add(n.project_id);
      return true;
    });
  }

  async function executeBatchDelete(projectIds) {
    try {
      var data = await apiFetch('/api/projects/delete-batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_ids: projectIds }),
      });

      var msg = 'Deleted ' + data.deleted_count + ' project(s).';
      if (data.errors && data.errors.length > 0) {
        msg += ' ' + data.errors.length + ' error(s) occurred.';
      }
      notify(msg, data.success ? 'success' : 'error');
      clearSelection();
      fetchTree();
    } catch (err) {
      notify('Deletion failed: ' + err.message, 'error');
    }
  }

  // -----------------------------------------------------------------------
  // Data fetch
  // -----------------------------------------------------------------------
  async function fetchTree() {
    setLoading(true);
    clearSelection();
    state.flatNodeMap.clear();

    try {
      var data = await apiFetch('/api/projects/tree');
      state.treeData = data;

      // Auto-expand to show structure for moderate tree sizes
      var total = data.total_projects || 0;
      if (total <= 50) {
        state.expandedIds.clear();
        data.projects.forEach(function (node) {
          expandAllRecursive(node);
        });
      } else {
        state.expandedIds.clear();
        data.projects.forEach(function (node) {
          if (node.children.length > 0) state.expandedIds.add(node.project_id);
          node.children.forEach(function (c) {
            if (c.children.length > 0) state.expandedIds.add(c.project_id);
          });
        });
      }

      renderTree();
      checkHealth();
      notify('Loaded ' + total + ' projects.', 'success');
    } catch (err) {
      $treeContent.innerHTML = '<div class="empty-state"><p>Failed to connect to CxSAST. Check that the server is running and your credentials in <code>backend/.env</code> are correct.</p><p style="font-size:0.85rem;color:#b2bec3;margin-top:8px">' + escapeHtml(err.message) + '</p></div>';
      notify('Failed to load projects: ' + err.message, 'error');
    } finally {
      setLoading(false);
    }
  }

  // -----------------------------------------------------------------------
  // Filtering
  // -----------------------------------------------------------------------
  var filterDebounceTimer = null;

  function applyFilter() {
    var textFilter = ($filterInput.value || '').trim().toLowerCase();
    var branchedOnly = $chkBranchedOnly.checked;

    var allNodes = $treeContent.querySelectorAll('.tree-node');
    var visibleCount = 0;

    for (var i = 0; i < allNodes.length; i++) {
      var li = allNodes[i];
      try {
        var pid = parseInt(li.dataset.projectId, 10);
        var node = state.flatNodeMap.get(pid);
        if (!node) continue;

        var name = (node.name != null ? String(node.name) : '');
        var nameMatch = !textFilter || name.toLowerCase().indexOf(textFilter) !== -1;
        var branchMatch = !branchedOnly || node.child_count > 0 || node.is_branched;

        if (nameMatch && branchMatch) {
          li.classList.remove('hidden');
          showAncestors(li);
          visibleCount++;
        } else {
          li.classList.add('hidden');
        }
      } catch (e) {
        // Skip nodes that cause errors (e.g., detached from DOM)
      }
    }

    // Show "no matches" hint
    var existing = document.getElementById('filter-no-match');
    if (textFilter && visibleCount === 0 && allNodes.length > 0) {
      if (!existing) {
        var hint = document.createElement('div');
        hint.id = 'filter-no-match';
        hint.className = 'empty-state';
        hint.innerHTML = '<p>No projects match "' + escapeHtml(textFilter) + '"</p>';
        $treeContent.appendChild(hint);
      }
    } else if (existing) {
      existing.remove();
    }
  }

  // Debounced wrapper for keystrokes
  function onFilterChange() {
    if (filterDebounceTimer) clearTimeout(filterDebounceTimer);
    filterDebounceTimer = setTimeout(applyFilter, 150);
  }

  function showAncestors(li) {
    var parent = li.parentElement;
    while (parent) {
      try {
        if (parent.classList.contains('tree-children')) {
          parent.classList.remove('collapsed');
          var parentLi = parent.parentElement;
          if (parentLi && parentLi.classList.contains('tree-node')) {
            parentLi.classList.remove('hidden');
          }
        }
      } catch (e) { /* skip broken DOM nodes */ }
      parent = parent.parentElement;
    }
  }

  // -----------------------------------------------------------------------
  // Modal
  // -----------------------------------------------------------------------
  function hideModal() {
    $modalOverlay.classList.add('hidden');
  }

  $modalClose.addEventListener('click', hideModal);
  $modalCancel.addEventListener('click', hideModal);
  $modalOverlay.addEventListener('click', function (e) {
    if (e.target === $modalOverlay) hideModal();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !$modalOverlay.classList.contains('hidden')) {
      hideModal();
    }
  });

  // -----------------------------------------------------------------------
  // Event bindings
  // -----------------------------------------------------------------------
  $btnRefresh.addEventListener('click', fetchTree);
  $btnDelete.addEventListener('click', function () {
    confirmAndDelete(null);
  });
  $btnExpandAll.addEventListener('click', expandAll);
  $btnCollapseAll.addEventListener('click', collapseAll);
  $filterInput.addEventListener('input', onFilterChange);
  $chkBranchedOnly.addEventListener('change', applyFilter);

  // -----------------------------------------------------------------------
  // Utilities
  // -----------------------------------------------------------------------
  function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  // -----------------------------------------------------------------------
  // Init
  // -----------------------------------------------------------------------
  checkHealth();
  fetchTree();
})();
