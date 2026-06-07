'use strict';

function initReport(reportData, suspects, emailMap) {
  const suspectSet = new Set(suspects);
  const edges = reportData.group.edges;
  const nodes = reportData.group.nodes.map(id => ({
    id,
    label: emailMap[id] || `S${id}`,
  }));

  let threshold = 0.6;

  // --- Threshold slider ---
  const slider = document.getElementById('threshold-slider');
  const thresholdDisplay = document.getElementById('threshold-value');
  slider.addEventListener('input', () => {
    threshold = parseFloat(slider.value);
    thresholdDisplay.textContent = threshold.toFixed(2);
    updateEdgeStyles();
    updateNodeStyles();
    renderSuspectPairs();
  });

  // --- D3 force graph ---
  const container = document.getElementById('similarity-graph');
  const width = container.parentElement.clientWidth;
  const height = 520;

  const svg = d3.select('#similarity-graph')
    .attr('viewBox', `0 0 ${width} ${height}`)
    .attr('preserveAspectRatio', 'xMidYMid meet');

  // Defs: arrow marker (unused but ready)
  svg.append('defs');

  const g = svg.append('g');

  // Zoom + pan
  svg.call(d3.zoom().scaleExtent([0.3, 4]).on('zoom', (event) => {
    g.attr('transform', event.transform);
  }));

  const linkGroup = g.append('g').attr('class', 'links');
  const nodeGroup = g.append('g').attr('class', 'nodes');

  // Build D3 link/node data
  const linkData = edges.map(e => ({
    source: e.student_a,
    target: e.student_b,
    score: e.score,
    details: e.details,
  }));

  const simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(linkData).id(d => d.id).distance(90))
    .force('charge', d3.forceManyBody().strength(-250))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide(55));

  // Draw links
  const link = linkGroup.selectAll('line')
    .data(linkData)
    .join('line')
    .attr('class', 'link')
    .attr('stroke-width', d => strokeWidth(d.score))
    .attr('stroke', d => edgeColor(d.score))
    .on('click', (event, d) => showModal(d));

  // Draw nodes
  const node = nodeGroup.selectAll('g')
    .data(nodes)
    .join('g')
    .attr('class', 'node')
    .call(d3.drag()
      .on('start', dragStart)
      .on('drag', dragged)
      .on('end', dragEnd));

  node.append('circle').attr('r', 16);

  node.each(function(d) {
    const text = d3.select(this).append('text').attr('y', 22);
    const parts = (d.label || '').split('@');
    text.append('tspan').attr('x', 0).text(parts[0]);
    if (parts.length > 1) {
      text.append('tspan').attr('x', 0).attr('dy', '1.1em').text('@' + parts[1]);
    }
  });

  node.append('title');

  function aboveThresholdIds() {
    const ids = new Set();
    edges.forEach(e => {
      if (e.score >= threshold) {
        ids.add(e.student_a);
        ids.add(e.student_b);
      }
    });
    return ids;
  }

  function updateNodeStyles() {
    const activeIds = aboveThresholdIds();
    nodeGroup.selectAll('.node circle')
      .attr('fill', d => activeIds.has(d.id) ? '#f38ba8' : '#89b4fa')
      .attr('stroke', d => activeIds.has(d.id) ? '#e06c75' : '#61afef');
    nodeGroup.selectAll('.node title')
      .text(d => `${emailMap[d.id] || 'Student ' + d.id}${activeIds.has(d.id) ? ' (suspect)' : ''}`);
  }

  updateNodeStyles();

  simulation.on('tick', () => {
    link
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y);

    node.attr('transform', d => `translate(${d.x},${d.y})`);
  });

  // --- Edge styling helpers ---
  function strokeWidth(score) {
    return score >= threshold ? 3 + score * 4 : 1.5;
  }

  function edgeColor(score) {
    return score >= threshold ? '#f38ba8' : '#585b70';
  }

  function updateEdgeStyles() {
    link
      .attr('stroke', d => edgeColor(d.score))
      .attr('stroke-width', d => strokeWidth(d.score));
  }

  // --- Drag handlers ---
  function dragStart(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x; d.fy = d.y;
  }
  function dragged(event, d) { d.fx = event.x; d.fy = event.y; }
  function dragEnd(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null; d.fy = null;
  }

  // --- Edge / suspect-pair modal ---
  const modal = document.getElementById('edge-modal');
  document.getElementById('modal-close').addEventListener('click', () => modal.close());
  modal.addEventListener('click', e => { if (e.target === modal) modal.close(); });

  function fmtDelta(tsA, tsB) {
    const diff = Math.round(Math.abs(new Date(tsA) - new Date(tsB)) / 1000);
    const m = Math.floor(diff / 60);
    const s = diff % 60;
    return m > 0 ? `${m} min ${s} sec apart` : `${s} sec apart`;
  }

  function fmtTime(ts) {
    return new Date(ts).toTimeString().slice(0, 8);
  }

  function showModal(d) {
    const aId = d.source.id ?? d.source;
    const bId = d.target.id ?? d.target;
    document.getElementById('modal-a').textContent = emailMap[aId] || `Student ${aId}`;
    document.getElementById('modal-b').textContent = emailMap[bId] || `Student ${bId}`;
    document.getElementById('modal-score').textContent = d.score.toFixed(4);
    document.getElementById('modal-cosine').textContent = (d.details.cosine ?? 0).toFixed(4);
    document.getElementById('modal-structural').textContent = (d.details.structural ?? 0).toFixed(4);
    document.getElementById('modal-sequential').textContent = (d.details.sequential ?? 0).toFixed(4);

    const seqSection = document.getElementById('modal-seq-matches');
    const seqList = document.getElementById('modal-seq-matches-list');
    const matches = d.details.sequential_matches;
    if (matches && matches.length > 0) {
      const n = matches.length;
      const seqScore = d.details.sequential ?? 0;

      const totalDeltaSec = matches.reduce((sum, m) => {
        return sum + Math.abs(new Date(m.timestamp_a) - new Date(m.timestamp_b)) / 1000;
      }, 0);
      const avgDeltaSec = Math.round(totalDeltaSec / n);
      const avgDeltaStr = avgDeltaSec === 0 ? '0 sec'
        : avgDeltaSec < 60 ? `${avgDeltaSec} sec`
        : `${Math.floor(avgDeltaSec / 60)} min ${avgDeltaSec % 60} sec`;

      const aFirstCount = matches.filter(m => m.who_first === 'a').length;
      const bFirstCount = n - aFirstCount;
      let directionSummary;
      if (aFirstCount === bFirstCount) {
        directionSummary = 'mixed direction';
      } else if (aFirstCount > bFirstCount) {
        directionSummary = `A committed first in ${aFirstCount} of ${n}`;
      } else {
        directionSummary = `B committed first in ${bFirstCount} of ${n}`;
      }

      const scoreColor = seqScore >= 0.6 ? '#f38ba8' : seqScore >= 0.3 ? '#fab387' : '#a6e3a1';
      const scorePct = Math.round(seqScore * 100);

      const statsHtml = `
        <div style="margin-bottom:0.75rem;padding:0.5rem;border-radius:var(--pico-border-radius);border:1px solid var(--pico-muted-border-color);">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.35rem;font-size:0.85em;flex-wrap:wrap;gap:0.25rem;">
            <span><strong>${n} sequential match${n !== 1 ? 'es' : ''}</strong></span>
            <span>avg \u0394 ${avgDeltaStr}</span>
            <span>${directionSummary}</span>
          </div>
          <div style="background:var(--pico-muted-border-color);border-radius:2px;height:8px;overflow:hidden;">
            <div style="background:${scoreColor};width:${scorePct}%;height:100%;"></div>
          </div>
          <div style="font-size:0.75em;text-align:right;margin-top:0.2rem;opacity:0.8;">Sequential score: ${seqScore.toFixed(4)}</div>
        </div>
      `;

      seqList.innerHTML = statsHtml + matches.map(m => {
        const deltaSec = Math.round(Math.abs(new Date(m.timestamp_a) - new Date(m.timestamp_b)) / 1000);
        const deltaLabel = deltaSec === 0 ? '\u0394 = 0'
          : deltaSec < 60 ? `+${deltaSec}s`
          : `+${Math.floor(deltaSec / 60)}m ${deltaSec % 60}s`;

        const dirBadge = m.who_first === 'a' ? 'A \u2192 B' : 'B \u2192 A';
        const firstTs = m.who_first === 'a' ? m.timestamp_a : m.timestamp_b;
        const secondTs = m.who_first === 'a' ? m.timestamp_b : m.timestamp_a;
        const firstLabel = m.who_first === 'a' ? 'A' : 'B';
        const secondLabel = m.who_first === 'a' ? 'B' : 'A';
        const firstColor = m.who_first === 'a' ? '#89b4fa' : '#f38ba8';
        const secondColor = m.who_first === 'a' ? '#f38ba8' : '#89b4fa';
        const exLabel = m.exercise_id ? `${escHtml(m.exercise_id)} / ${escHtml(m.file_name)}` : '';

        return `
          <div style="border:1px solid var(--pico-muted-border-color);border-radius:var(--pico-border-radius);padding:0.5rem;margin-bottom:0.5rem;">
            <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.25rem;flex-wrap:wrap;">
              <strong>${dirBadge}</strong>
              <mark>${(m.similarity * 100).toFixed(0)}% token similarity</mark>
              ${exLabel ? `<span style="font-size:0.8em;opacity:0.8;">${exLabel}</span>` : ''}
            </div>
            <div style="display:flex;align-items:center;gap:0.4rem;margin:0.35rem 0;font-size:0.8em;font-family:monospace;">
              <div style="text-align:center;min-width:2.8rem;">
                <div style="background:${firstColor};width:10px;height:10px;border-radius:50%;margin:0 auto;"></div>
                <span>[${firstLabel}]</span><br>
                <span style="font-size:0.85em;opacity:0.8;">${fmtTime(firstTs)}</span>
              </div>
              <div style="flex:1;display:flex;flex-direction:column;align-items:center;">
                <div style="border-top:2px solid var(--pico-muted-border-color);width:100%;"></div>
                <span style="font-size:0.85em;margin-top:0.15rem;">${deltaLabel}</span>
              </div>
              <div style="text-align:center;min-width:2.8rem;">
                <div style="background:${secondColor};width:10px;height:10px;border-radius:50%;margin:0 auto;"></div>
                <span>[${secondLabel}]</span><br>
                <span style="font-size:0.85em;opacity:0.8;">${fmtTime(secondTs)}</span>
              </div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;">
              <pre style="margin:0;font-size:0.75em;overflow:auto;max-height:160px;">${escHtml(m.diff_a)}</pre>
              <pre style="margin:0;font-size:0.75em;overflow:auto;max-height:160px;">${escHtml(m.diff_b)}</pre>
            </div>
          </div>
        `;
      }).join('');
      seqSection.hidden = false;
    } else {
      seqSection.hidden = true;
    }

    modal.showModal();
  }

  function escHtml(str) {
    return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  // --- Suspect pairs table ---
  const tbody = document.getElementById('suspect-pairs-body');
  let currentPairs = [];

  function renderSuspectPairs() {
    currentPairs = edges
      .filter(e => e.score >= threshold)
      .sort((a, b) => b.score - a.score);

    if (!currentPairs.length) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center">No pairs above threshold</td></tr>';
      return;
    }

    tbody.innerHTML = currentPairs.map((e, idx) => `
      <tr class="suspect-row" data-idx="${idx}" style="cursor:pointer">
        <td>${emailMap[e.student_a] || 'S' + e.student_a}</td>
        <td>${emailMap[e.student_b] || 'S' + e.student_b}</td>
        <td>${e.score.toFixed(4)}</td>
        <td>${(e.details.cosine ?? 0).toFixed(4)}</td>
        <td>${(e.details.structural ?? 0).toFixed(4)}</td>
        <td>${(e.details.sequential ?? 0).toFixed(4)}</td>
      </tr>
    `).join('');
  }

  tbody.addEventListener('click', event => {
    const row = event.target.closest('tr.suspect-row');
    if (!row) return;
    const e = currentPairs[parseInt(row.dataset.idx)];
    showModal({ source: e.student_a, target: e.student_b, score: e.score, details: e.details });
  });

  renderSuspectPairs();

  // --- Anomaly detail modal ---
  const anomalyModal = document.getElementById('anomaly-modal');
  document.getElementById('anomaly-modal-close').addEventListener('click', () => anomalyModal.close());
  anomalyModal.addEventListener('click', e => { if (e.target === anomalyModal) anomalyModal.close(); });

  const FLAG_LABELS = { burst: 'Code Burst', late_start: 'Late Start', inactivity_gap: 'Inactivity Gap' };

  function showAnomalyModal(ind) {
    document.getElementById('anomaly-student').textContent = emailMap[ind.student_id] || `Student ${ind.student_id}`;
    document.getElementById('anomaly-score').textContent = ind.anomaly_score.toFixed(4);
    const flagList = document.getElementById('anomaly-flags');
    if (!ind.events.length) {
      flagList.innerHTML = '<li>No suspicious patterns detected</li>';
    } else {
      flagList.innerHTML = ind.events.map(ev => {
        const label = FLAG_LABELS[ev.type] || ev.type;
        const detail = ev.detail && ev.detail !== 'stored' ? `: ${ev.detail}` : '';
        const ts = ev.timestamp && ev.timestamp !== 'stored' && ev.timestamp !== '' ? ` @ ${ev.timestamp}` : '';
        return `<li><strong>${label}</strong>${detail}${ts}</li>`;
      }).join('');
    }
    anomalyModal.showModal();
  }

  document.getElementById('anomaly-tbody').addEventListener('click', event => {
    const row = event.target.closest('tr[data-student-id]');
    if (!row) return;
    const sid = parseInt(row.dataset.studentId);
    const ind = reportData.individual.find(i => i.student_id === sid);
    if (ind) showAnomalyModal(ind);
  });
}
