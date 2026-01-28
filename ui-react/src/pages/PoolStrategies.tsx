import { Fragment, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  Info,
  Loader2,
  PlayCircle,
  Shuffle,
  Trash2,
  Zap,
} from 'lucide-react'

interface PoolStrategy {
  id: number
  name: string
  strategy_type: 'round_robin' | 'load_balance' | 'pro_mode' | string
  enabled: boolean
  pool_ids: number[]
  miner_ids: number[]
  config: Record<string, unknown>
  current_pool_index: number
  last_switch: string | null
}

const STRATEGY_META: Record<string, { label: string; tone: string; description: string }> = {
  round_robin: {
    label: 'Round Robin',
    tone: 'bg-sky-500/10 text-sky-300 border-sky-500/30',
    description: 'Rotates miners through pools at fixed intervals',
  },
  load_balance: {
    label: 'Load Balance',
    tone: 'bg-purple-500/10 text-purple-300 border-purple-500/30',
    description: 'Distributes miners based on pool health and latency',
  },
  pro_mode: {
    label: 'Pro Mode',
    tone: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
    description: 'Switches pools based on Agile pricing bands',
  },
}

type Banner = { type: 'success' | 'error'; message: string } | null

const STATUS_CLASSES = {
  active: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  inactive: 'bg-slate-700/40 text-slate-300 border-slate-600/60',
}

const STRATEGY_GUIDE_SECTIONS = [
  {
    title: 'Round Robin',
    accent: 'text-sky-300',
    icon: <Shuffle className="h-4 w-4" />,
    body: [
      'Rotates all enrolled miners through the selected pools on a timer.',
      'Ideal for sharing hashrate between multiple solo pools to reduce variance.',
      'Keeps the fleet together so every miner hits the same pool simultaneously.',
    ],
    tip: 'Set the interval to align with pool payout cadence (e.g., every 60 minutes).',
  },
  {
    title: 'Load Balance',
    accent: 'text-purple-300',
    icon: <Zap className="h-4 w-4" />,
    body: [
      'Scores pools based on health, latency, and reject rate to keep miners on the best performers.',
      'Distributes miners proportionally so the healthiest pools receive more hashrate.',
      'Great for minimizing downtime and keeping Avalon + Bitaxe rigs productive.',
    ],
    tip: 'Increase the minimum health threshold if you only want near-perfect pools considered.',
  },
  {
    title: 'Pro Mode',
    accent: 'text-amber-300',
    icon: <Info className="h-4 w-4" />,
    body: [
      'Pairs with Energy Optimization to switch between “cheap” and “expensive” pools.',
      'Requires Agile pricing to be enabled and configured.',
      'Perfect for separating efficient pools from higher-paying high-risk pools.',
    ],
    tip: 'Use aggressive dwell hours so miners are not flapping during brief price spikes.',
  },
]

function formatTimestamp(value: string | null) {
  if (!value) return 'Never'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return `${date.toLocaleDateString()} · ${date.toLocaleTimeString()}`
}

function formatSummary(strategy: PoolStrategy) {
  if (strategy.strategy_type === 'round_robin') {
    const minutes = (strategy.config?.interval_minutes as number) || 60
    return `${minutes} min interval`
  }
  if (strategy.strategy_type === 'load_balance') {
    const minHealth = (strategy.config?.min_health_threshold as number) ?? 50
    return `Min health ${minHealth}`
  }
  if (strategy.strategy_type === 'pro_mode') {
    const threshold = (strategy.config?.price_threshold as number) ?? 15
    return `Threshold ${threshold} p/kWh`
  }
  return 'Custom strategy'
}

async function fetchStrategies(): Promise<PoolStrategy[]> {
  const response = await fetch('/api/pools/strategies')
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || 'Failed to load strategies')
  }
  return response.json()
}

export default function PoolStrategies() {
  const queryClient = useQueryClient()
  const [guideOpen, setGuideOpen] = useState(false)
  const [banner, setBanner] = useState<Banner>(null)
  const [confirmingId, setConfirmingId] = useState<number | null>(null)

  const {
    data: strategies = [],
    isLoading,
    error,
  } = useQuery<PoolStrategy[]>({
    queryKey: ['pool-strategies'],
    queryFn: fetchStrategies,
    refetchInterval: 60000,
  })

  const [executingId, setExecutingId] = useState<number | null>(null)
  const executeMutation = useMutation({
    mutationFn: async (strategyId: number) => {
      const response = await fetch(`/api/pools/strategies/${strategyId}/execute`, {
        method: 'POST',
      })
      if (!response.ok) {
        const body = await response.json().catch(() => ({}))
        throw new Error(body.detail || 'Failed to execute strategy')
      }
      return response.json()
    },
    onMutate: (strategyId) => setExecutingId(strategyId),
    onSuccess: () => {
      setBanner({ type: 'success', message: 'Strategy execution triggered' })
      queryClient.invalidateQueries({ queryKey: ['pool-strategies'] })
    },
    onError: (mutationError: Error) => {
      setBanner({ type: 'error', message: mutationError.message })
    },
    onSettled: () => setExecutingId(null),
  })

  const deleteMutation = useMutation({
    mutationFn: async (strategyId: number) => {
      const response = await fetch(`/api/pools/strategies/${strategyId}`, {
        method: 'DELETE',
      })
      if (!response.ok) {
        const body = await response.json().catch(() => ({}))
        throw new Error(body.detail || 'Failed to delete strategy')
      }
      return response.json()
    },
    onMutate: (strategyId) => setConfirmingId(strategyId),
    onSuccess: () => {
      setBanner({ type: 'success', message: 'Strategy deleted' })
      queryClient.invalidateQueries({ queryKey: ['pool-strategies'] })
    },
    onError: (mutationError: Error) => setBanner({ type: 'error', message: mutationError.message }),
    onSettled: () => setConfirmingId(null),
  })

  const summary = useMemo(() => {
    const total = strategies.length
    const active = strategies.filter((strategy) => strategy.enabled).length
    const inactive = total - active
    return { total, active, inactive }
  }, [strategies])

  const handleExecute = (strategy: PoolStrategy) => {
    if (!strategy.enabled) return
    if (!window.confirm(`Execute "${strategy.name}" now? Miners will switch immediately.`)) return
    executeMutation.mutate(strategy.id)
  }

  const handleDelete = (strategy: PoolStrategy) => {
    if (!window.confirm(`Delete "${strategy.name}"? This cannot be undone.`)) return
    deleteMutation.mutate(strategy.id)
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="space-y-1">
          <p className="text-xs uppercase tracking-[0.3em] text-blue-300">Miner Management</p>
          <h1 className="text-2xl font-semibold">Pool Strategies</h1>
          <p className="text-sm text-muted-foreground">
            Automate pool switching with round robin, load balancing, or price-aware flows.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" className="gap-2" onClick={() => setGuideOpen(true)}>
            <BookOpen className="h-4 w-4" /> Strategy Guide
          </Button>
          <Button asChild className="gap-2">
            <a href="/pools/strategies/add">
              <Shuffle className="h-4 w-4" /> Add Strategy
            </a>
          </Button>
        </div>
      </div>

      {banner && (
        <div
          className={`rounded-md border px-4 py-3 text-sm ${
            banner.type === 'success'
              ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-100'
              : 'border-red-500/40 bg-red-500/10 text-red-100'
          }`}
        >
          {banner.message}
        </div>
      )}

      {error && (
        <div className="flex items-center gap-3 rounded-md border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          <AlertTriangle className="h-4 w-4" />
          <span>{error instanceof Error ? error.message : 'Unable to load strategies'}</span>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="p-5">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Total Strategies</p>
            <p className="mt-2 text-3xl font-semibold">{summary.total}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Active</p>
            <div className="mt-2 flex items-baseline gap-2">
              <p className="text-3xl font-semibold text-emerald-300">{summary.active}</p>
              <span className="text-sm text-muted-foreground">running</span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Paused</p>
            <div className="mt-2 flex items-baseline gap-2">
              <p className="text-3xl font-semibold text-amber-300">{summary.inactive}</p>
              <span className="text-sm text-muted-foreground">waiting</span>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-xl font-semibold">Strategies</h2>
              <p className="text-sm text-muted-foreground">Monitor automation flows and trigger manual runs when needed.</p>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex min-h-[240px] items-center justify-center text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : strategies.length === 0 ? (
            <div className="rounded-lg border border-dashed border-border bg-background p-10 text-center">
              <Shuffle className="mx-auto mb-4 h-10 w-10 text-muted-foreground" />
              <p className="text-lg font-medium">No pool strategies yet</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Combine multiple pools with automation logic to keep miners productive.
              </p>
              <Button className="mt-4" asChild>
                <a href="/pools/strategies/add">Add Your First Strategy</a>
              </Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-4 py-3">Strategy</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3">Pools / Miners</th>
                    <th className="px-4 py-3">Last Switch</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {strategies.map((strategy) => {
                    const meta = STRATEGY_META[strategy.strategy_type] || {
                      label: strategy.strategy_type,
                      tone: 'bg-slate-700/40 text-slate-200 border-slate-600/50',
                      description: 'Custom flow',
                    }
                    const statusClass = strategy.enabled ? STATUS_CLASSES.active : STATUS_CLASSES.inactive

                    return (
                      <tr key={strategy.id} className="border-b border-border/60">
                        <td className="px-4 py-4">
                          <div className="font-semibold text-foreground">{strategy.name}</div>
                          <p className="text-xs text-muted-foreground">{formatSummary(strategy)}</p>
                        </td>
                        <td className="px-4 py-4">
                          <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${meta.tone}`}>
                            {meta.label}
                          </span>
                        </td>
                        <td className="px-4 py-4">
                          <div className="text-sm text-foreground">{strategy.pool_ids.length} pools</div>
                          <p className="text-xs text-muted-foreground">
                            {strategy.miner_ids.length > 0
                              ? `${strategy.miner_ids.length} miners`
                              : 'Applies to all miners'}
                          </p>
                        </td>
                        <td className="px-4 py-4 text-sm text-muted-foreground">{formatTimestamp(strategy.last_switch)}</td>
                        <td className="px-4 py-4">
                          <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-semibold ${statusClass}`}>
                            {strategy.enabled ? (
                              <>
                                <CheckCircle2 className="h-3.5 w-3.5" /> Active
                              </>
                            ) : (
                              <>
                                <AlertTriangle className="h-3.5 w-3.5" /> Paused
                              </>
                            )}
                          </span>
                        </td>
                        <td className="px-4 py-4">
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              variant="secondary"
                              size="sm"
                              className="gap-1"
                              disabled={!strategy.enabled || executingId === strategy.id}
                              onClick={() => handleExecute(strategy)}
                            >
                              {executingId === strategy.id ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <PlayCircle className="h-4 w-4" />
                              )}
                              Run
                            </Button>
                            <Button variant="outline" size="sm" className="gap-1" asChild>
                              <a href={`/pools/strategies/${strategy.id}/edit`}>
                                <Info className="h-4 w-4" /> Edit
                              </a>
                            </Button>
                            <Button
                              variant="destructive"
                              size="sm"
                              className="gap-1"
                              disabled={confirmingId === strategy.id}
                              onClick={() => handleDelete(strategy)}
                            >
                              {confirmingId === strategy.id ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <Trash2 className="h-4 w-4" />
                              )}
                              Delete
                            </Button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Shuffle className="h-5 w-5 text-blue-300" />
            <div>
              <h2 className="text-xl font-semibold">Strategy Primer</h2>
              <p className="text-sm text-muted-foreground">Quick comparisons to decide which automation fits your fleet.</p>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            {STRATEGY_GUIDE_SECTIONS.map((section) => (
              <div key={section.title} className="rounded-xl border border-border/80 bg-muted/10 p-4">
                <div className={`flex items-center gap-2 text-sm font-semibold ${section.accent}`}>
                  {section.icon}
                  {section.title}
                </div>
                <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
                  {section.body.map((item) => (
                    <li key={item} className="flex items-start gap-2">
                      <span className="mt-1 h-1.5 w-1.5 rounded-full bg-muted-foreground/60" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
                <div className="mt-3 rounded-md border border-dashed border-border/70 bg-background/60 p-3 text-xs text-muted-foreground">
                  <strong className="font-semibold text-foreground">Tip:</strong> {section.tip}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Dialog open={guideOpen} onOpenChange={setGuideOpen}>
        <DialogContent className="max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <BookOpen className="h-5 w-5" /> Pool Strategy Guide
            </DialogTitle>
            <DialogDescription>
              Deep dive into how each automation mode behaves and when to use it.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-6 text-sm text-muted-foreground">
            {STRATEGY_GUIDE_SECTIONS.map((section) => (
              <Fragment key={section.title}>
                <div>
                  <h3 className="flex items-center gap-2 text-lg font-semibold text-foreground">
                    {section.icon}
                    {section.title}
                  </h3>
                  <ul className="mt-2 space-y-2">
                    {section.body.map((item) => (
                      <li key={item} className="leading-relaxed">
                        {item}
                      </li>
                    ))}
                  </ul>
                  <div className="mt-3 rounded-md border border-info/30 bg-info/5 p-3 text-sm text-foreground">
                    <strong>Pro tip:</strong> {section.tip}
                  </div>
                </div>
              </Fragment>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
