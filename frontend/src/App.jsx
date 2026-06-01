import { useState, useEffect, useCallback } from 'react'

const API_BASE = '/api'

const TYPE_COLORS = {
  CONSTRAINT: { bg: 'bg-red-100', text: 'text-red-800', border: 'border-red-400', emoji: '🔴' },
  DECISION: { bg: 'bg-yellow-100', text: 'text-yellow-800', border: 'border-yellow-400', emoji: '🟡' },
  ANTI_PATTERN: { bg: 'bg-orange-100', text: 'text-orange-800', border: 'border-orange-400', emoji: '🟠' },
  FACT: { bg: 'bg-blue-100', text: 'text-blue-800', border: 'border-blue-400', emoji: '🔵' },
}

const ZONE_LABELS = { 1: 'ADDRESSED', 2: 'GLOBAL', 3: 'FLOATING' }

function App() {
  const [users, setUsers] = useState([])
  const [selectedUser, setSelectedUser] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [compareUsers, setCompareUsers] = useState([])
  const [compareResults, setCompareResults] = useState(null)
  const [includeZone2, setIncludeZone2] = useState(true)
  const [stats, setStats] = useState(null)

  useEffect(() => {
    fetch(`${API_BASE}/users`).then(r => r.json()).then(setUsers).catch(console.error)
    fetch(`${API_BASE}/stats`).then(r => r.json()).then(setStats).catch(console.error)
  }, [])

  const runPipeline = useCallback(async () => {
    if (!selectedUser) return
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/pipeline/run?user_id=${selectedUser}&include_zone2=${includeZone2}`)
      const data = await res.json()
      setResult(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [selectedUser, includeZone2])

  const runComparison = useCallback(async () => {
    if (compareUsers.length < 2) return
    setLoading(true)
    try {
      const ids = compareUsers.join('&user_ids=')
      const res = await fetch(`${API_BASE}/pipeline/compare?${ids}&include_zone2=${includeZone2}`)
      const data = await res.json()
      setCompareResults(data.comparisons || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [compareUsers, includeZone2])

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <div className="bg-gray-900 border-b border-gray-800 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">BRAHMO Rules Engine</h1>
            <p className="text-gray-400 text-sm mt-1">BFS Traversal + 5-Check Filter Pipeline — Zero LLM</p>
          </div>
          {stats && (
            <div className="flex gap-6 text-sm text-gray-400">
              <span>📊 {stats.total_nodes} nodes</span>
              <span>👤 {stats.total_users} users</span>
              <span>🏥 {stats.total_levels} levels</span>
            </div>
          )}
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-6">
        {/* User Selection + Controls */}
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 mb-6">
          <div className="flex flex-wrap items-end gap-4">
            <div className="flex-1 min-w-64">
              <label className="block text-sm font-medium text-gray-400 mb-2">Select User</label>
              <select
                value={selectedUser}
                onChange={e => setSelectedUser(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">-- Choose a user profile --</option>
                {users.map(u => (
                  <option key={u.id} value={u.id}>
                    {u.name} — {u.role}, L{u.ceiling_level}, {u.department}
                    {u.compliance_clearance?.length > 0 ? ` [${u.compliance_clearance.join(', ')}]` : ''}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="zone2"
                checked={includeZone2}
                onChange={e => setIncludeZone2(e.target.checked)}
                className="w-4 h-4 rounded border-gray-600 bg-gray-800 text-blue-500 focus:ring-blue-500"
              />
              <label htmlFor="zone2" className="text-sm text-gray-400">Include Zone 2 (GLOBAL)</label>
            </div>
            <button
              onClick={runPipeline}
              disabled={!selectedUser || loading}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 text-white font-medium px-6 py-3 rounded-lg transition-colors"
            >
              {loading ? '⏳ Running...' : '▶ Run Pipeline'}
            </button>
          </div>
        </div>

        {/* Results */}
        {result && !result.error && (
          <div className="space-y-6">
            {/* User Info */}
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center text-lg font-bold">
                  {result.user.name[0]}
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-white">{result.user.name}</h2>
                  <p className="text-sm text-gray-400">
                    {result.user.role} · Level {result.user.ceiling_level} · {result.user.department}
                    {result.user.compliance_clearance?.length > 0 ? ` · Clearance: ${result.user.compliance_clearance.join(', ')}` : ''}
                  </p>
                </div>
              </div>
              <div className="flex flex-wrap gap-4 text-sm">
                <span className="bg-gray-800 px-3 py-1 rounded-full">
                  Entry: <span className="font-mono text-blue-400">{result.entry_point?.level_name}</span> (L{result.entry_point?.level_number})
                </span>
                <span className="bg-green-900/50 text-green-400 px-3 py-1 rounded-full">
                  {result.candidate_count} candidates
                </span>
                <span className="bg-gray-800 px-3 py-1 rounded-full">
                  ⚡ {result.pipeline_timing?.total_ms}ms
                </span>
                <span className="bg-gray-800 px-3 py-1 rounded-full">
                  🚫 Zero LLM calls
                </span>
              </div>
            </div>

            {/* Filter Funnel */}
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Filter Funnel</h3>
              <div className="space-y-2">
                {[
                  { label: 'Total Graph', count: result.funnel.total_nodes, color: 'bg-gray-600' },
                  { label: 'BFS Reachable', count: result.funnel.after_bfs, color: 'bg-blue-600' },
                  { label: '+ Zone 2 (GLOBAL)', count: result.funnel.after_zone2, color: 'bg-indigo-600' },
                  { label: '✓ Check 1: Isolation', count: result.funnel.after_isolation, color: 'bg-purple-600' },
                  { label: '✓ Check 2: Compliance', count: result.funnel.after_compliance, color: 'bg-pink-600' },
                  { label: '✓ Check 3: Permission', count: result.funnel.after_permission, color: 'bg-amber-600' },
                  { label: '✓ Check 4: Temporal', count: result.funnel.after_temporal, color: 'bg-orange-600' },
                  { label: '✓ Check 5: Derivability', count: result.funnel.after_derivability, color: 'bg-green-600' },
                ].map((step, i) => {
                  const maxCount = result.funnel.total_nodes
                  const width = maxCount > 0 ? (step.count / maxCount) * 100 : 0
                  return (
                    <div key={i} className="flex items-center gap-3">
                      <div className="w-48 text-sm text-gray-400 text-right">{step.label}</div>
                      <div className="flex-1 bg-gray-800 rounded-full h-8 overflow-hidden">
                        <div
                          className={`${step.color} h-full rounded-full flex items-center px-3 transition-all duration-500`}
                          style={{ width: `${Math.max(width, 2)}%` }}
                        >
                          <span className="text-white text-sm font-mono font-bold">{step.count}</span>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Pipeline Timing */}
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Pipeline Timing</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {Object.entries(result.pipeline_timing || {}).map(([key, val]) => (
                  <div key={key} className="bg-gray-800 rounded-lg p-3">
                    <div className="text-xs text-gray-500 uppercase">{key.replace(/_/g, ' ').replace(' ms', '')}</div>
                    <div className="text-xl font-mono font-bold text-white">{val}<span className="text-xs text-gray-500">ms</span></div>
                  </div>
                ))}
              </div>
            </div>

            {/* Candidate Set */}
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
              <h3 className="text-lg font-semibold text-white mb-4">
                Candidate Set ({result.candidate_count} nodes)
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-800">
                      <th className="text-left py-2 px-3 text-gray-500">Type</th>
                      <th className="text-left py-2 px-3 text-gray-500">Title</th>
                      <th className="text-left py-2 px-3 text-gray-500">Zone</th>
                      <th className="text-left py-2 px-3 text-gray-500">Dept</th>
                      <th className="text-center py-2 px-3 text-gray-500">Dist</th>
                      <th className="text-center py-2 px-3 text-gray-500">Score</th>
                      <th className="text-left py-2 px-3 text-gray-500">Hint</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.candidate_set.map(node => {
                      const tc = TYPE_COLORS[node.type] || TYPE_COLORS.FACT
                      return (
                        <tr key={node.id} className="border-b border-gray-800/50 hover:bg-gray-800/50">
                          <td className="py-2 px-3">
                            <span className={`${tc.bg} ${tc.text} ${tc.border} border px-2 py-0.5 rounded text-xs font-medium`}>
                              {tc.emoji} {node.type}
                            </span>
                          </td>
                          <td className="py-2 px-3 text-white font-medium" title={node.content}>
                            {node.title.length > 55 ? node.title.slice(0, 55) + '…' : node.title}
                          </td>
                          <td className="py-2 px-3">
                            <span className={`text-xs px-2 py-0.5 rounded ${node.zone === 2 ? 'bg-indigo-900 text-indigo-300' : 'bg-gray-800 text-gray-400'}`}>
                              {ZONE_LABELS[node.zone] || 'Z1'}
                            </span>
                          </td>
                          <td className="py-2 px-3 text-gray-400">{node.department || '—'}</td>
                          <td className="py-2 px-3 text-center font-mono text-gray-300">{node.distance_from_entry}</td>
                          <td className="py-2 px-3 text-center font-mono text-gray-300">{node.importance.toFixed(2)}</td>
                          <td className="py-2 px-3">
                            <span className={`text-xs px-2 py-0.5 rounded ${
                              node.compression_hint === 'FULL' ? 'bg-green-900 text-green-300' :
                              node.compression_hint === 'COMPRESSED' ? 'bg-amber-900 text-amber-300' :
                              'bg-red-900 text-red-300'
                            }`}>
                              {node.compression_hint}
                            </span>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Silent Exclusion Check */}
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
              <h3 className="text-lg font-semibold text-white mb-4">🔒 Silent Exclusion Verification</h3>
              <p className="text-gray-400 text-sm mb-3">
                Zero nodes from unauthorized departments. No "access denied" messages. Nodes are absent, not denied.
              </p>
              <div className="flex flex-wrap gap-2">
                {['cardiology', 'paediatrics', 'icu', 'surgery'].map(dept => {
                  const found = result.candidate_set.some(n => n.department === dept)
                  return (
                    <span key={dept} className={`px-3 py-1 rounded text-sm ${found ? 'bg-red-900 text-red-300' : 'bg-green-900/30 text-green-500'}`}>
                      {found ? '❌' : '✅'} {dept}: {found ? 'LEAKED' : 'absent'}
                    </span>
                  )
                })}
              </div>
            </div>
          </div>
        )}

        {/* Comparison View */}
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 mt-6">
          <h3 className="text-lg font-semibold text-white mb-4">👥 Compare Users</h3>
          <p className="text-gray-400 text-sm mb-4">Select 2-3 users to compare side by side. Same graph, different results.</p>
          <div className="flex flex-wrap gap-3 mb-4">
            {users.map(u => (
              <label key={u.id} className={`flex items-center gap-2 px-3 py-2 rounded-lg border cursor-pointer transition-colors ${
                compareUsers.includes(u.id) ? 'bg-blue-600/20 border-blue-500' : 'bg-gray-800 border-gray-700 hover:border-gray-600'
              }`}>
                <input
                  type="checkbox"
                  checked={compareUsers.includes(u.id)}
                  onChange={e => {
                    if (e.target.checked) {
                      setCompareUsers(prev => [...prev, u.id].slice(0, 3))
                    } else {
                      setCompareUsers(prev => prev.filter(id => id !== u.id))
                    }
                  }}
                  className="w-3 h-3"
                />
                <span className="text-sm">{u.name} ({u.role})</span>
              </label>
            ))}
          </div>
          <button
            onClick={runComparison}
            disabled={compareUsers.length < 2 || loading}
            className="bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 text-white px-4 py-2 rounded-lg text-sm"
          >
            Compare {compareUsers.length} Users
          </button>

          {compareResults && compareResults.length > 0 && (
            <div className="mt-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {compareResults.map((cr, i) => (
                  <div key={i} className="bg-gray-800 rounded-lg p-4 border border-gray-700">
                    <div className="text-lg font-bold text-white">{cr.user.name}</div>
                    <div className="text-sm text-gray-400 mb-3">{cr.user.role} · L{cr.user.ceiling_level} · {cr.user.department}</div>
                    <div className="text-3xl font-mono font-bold text-blue-400 mb-2">{cr.candidate_count}</div>
                    <div className="text-xs text-gray-500 mb-3">candidate nodes</div>
                    <div className="space-y-1 text-sm">
                      <div className="flex justify-between"><span className="text-gray-500">BFS reach:</span><span className="text-gray-300">{cr.funnel.after_bfs}</span></div>
                      <div className="flex justify-between"><span className="text-gray-500">+ Zone 2:</span><span className="text-gray-300">{cr.funnel.after_zone2}</span></div>
                      <div className="flex justify-between"><span className="text-gray-500">After checks:</span><span className="text-green-400">{cr.candidate_count}</span></div>
                      <div className="flex justify-between"><span className="text-gray-500">Time:</span><span className="text-gray-300">{cr.pipeline_timing?.total_ms}ms</span></div>
                    </div>
                    <div className="mt-3 pt-3 border-t border-gray-700 space-y-1">
                      <div className="text-xs text-gray-500">Departments visible:</div>
                      <div className="flex flex-wrap gap-1">
                        {[...new Set(cr.candidate_set.map(n => n.department || 'GLOBAL'))].sort().map(dept => (
                          <span key={dept} className={`text-xs px-1.5 py-0.5 rounded ${
                            dept === 'GLOBAL' ? 'bg-indigo-900/50 text-indigo-300' : 'bg-gray-700 text-gray-300'
                          }`}>{dept}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default App