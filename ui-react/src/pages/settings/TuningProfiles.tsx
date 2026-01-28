import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertCircle,
  Loader2,
  Plus,
  SlidersHorizontal,
  Trash2,
  Zap,
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { APIError, minersAPI, Miner, tuningAPI, TuningProfile } from '@/lib/api'
import { cn } from '@/lib/utils'

type MinerType = 'avalon_nano' | 'bitaxe' | 'nerdqaxe'

interface BannerState {
  tone: 'success' | 'error' | 'info'
  message: string
}

const MINER_TYPE_OPTIONS: { value: MinerType; label: string }[] = [
  { value: 'avalon_nano', label: 'Avalon Nano 3/3S' },
  { value: 'bitaxe', label: 'Bitaxe 601' },
  { value: 'nerdqaxe', label: 'NerdQaxe++' },
]

const ALL_TYPES_VALUE = 'all'

interface CreateProfileForm {
  name: string
  minerType: MinerType | ''
  description: string
  mode: string
  frequency: string
  voltage: string
}

const INITIAL_FORM: CreateProfileForm = {
  name: '',
  minerType: '',
  description: '',
  mode: 'standard',
  frequency: '',
  voltage: '',
}

export default function TuningProfiles() {
  const queryClient = useQueryClient()
  const [filter, setFilter] = useState<string>(ALL_TYPES_VALUE)
  const [banner, setBanner] = useState<BannerState | null>(null)
  const [isCreateOpen, setCreateOpen] = useState(false)
  const [createForm, setCreateForm] = useState<CreateProfileForm>(INITIAL_FORM)
  const [formError, setFormError] = useState<string | null>(null)
  const [applyProfile, setApplyProfile] = useState<TuningProfile | null>(null)
  const [selectedMinerId, setSelectedMinerId] = useState<string>('')
  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null)

  const profilesQuery = useQuery({
    queryKey: ['tuning-profiles', filter],
    queryFn: () =>
      tuningAPI.getProfiles(filter === ALL_TYPES_VALUE ? undefined : filter),
  })

  const minersQuery = useQuery({
    queryKey: ['miners-for-apply'],
    queryFn: () => minersAPI.getAll(),
    enabled: Boolean(applyProfile),
  })

  const showBanner = (tone: BannerState['tone'], message: string) => {
    setBanner({ tone, message })
    window.setTimeout(() => setBanner(null), 5000)
  }

  const extractError = (error: unknown) => {
    if (error instanceof APIError) {
      if (error.data && typeof error.data === 'object') {
        const detail = (error.data as { detail?: unknown }).detail
        if (typeof detail === 'string') {
          return detail
        }
      }
      return error.message
    }
    if (error instanceof Error) return error.message
    return 'Something went wrong'
  }

  const createMutation = useMutation({
    mutationFn: tuningAPI.createProfile,
    onSuccess: () => {
      showBanner('success', 'Tuning profile created')
      queryClient.invalidateQueries({ queryKey: ['tuning-profiles'] })
      setCreateOpen(false)
      setCreateForm(INITIAL_FORM)
    },
    onError: (error) => setFormError(extractError(error)),
  })

  const deleteMutation = useMutation({
    mutationFn: (profileId: number) => tuningAPI.deleteProfile(profileId),
    onSuccess: () => {
      showBanner('success', 'Profile deleted')
      queryClient.invalidateQueries({ queryKey: ['tuning-profiles'] })
    },
    onError: (error) => showBanner('error', extractError(error)),
    onSettled: () => setPendingDeleteId(null),
  })

  const applyMutation = useMutation({
    mutationFn: ({ profileId, minerId }: { profileId: number; minerId: number }) =>
      tuningAPI.applyProfile(profileId, minerId),
    onSuccess: (response) => {
      showBanner('success', response.message || 'Profile applied successfully')
      setApplyProfile(null)
      setSelectedMinerId('')
    },
    onError: (error) => showBanner('error', extractError(error)),
  })

  const filteredMiners: Miner[] = useMemo(() => {
    if (!applyProfile || !minersQuery.data) return []
    return minersQuery.data.filter((miner) => miner.type === applyProfile.miner_type)
  }, [applyProfile, minersQuery.data])

  const handleSaveProfile = () => {
    setFormError(null)
    if (!createForm.name.trim()) {
      setFormError('Profile name is required')
      return
    }
    if (!createForm.minerType) {
      setFormError('Select a miner type')
      return
    }

    const settings: Record<string, string | number> = {}
    if (createForm.minerType === 'avalon_nano') {
      settings.mode = createForm.mode || 'med'
    } else {
      if (createForm.mode) settings.mode = createForm.mode
      if (createForm.frequency) settings.frequency = Number(createForm.frequency)
      if (createForm.voltage) settings.voltage = Number(createForm.voltage)
    }

    if (Object.keys(settings).length === 0) {
      setFormError('Configure at least one setting')
      return
    }

    createMutation.mutate({
      name: createForm.name.trim(),
      miner_type: createForm.minerType,
      description: createForm.description.trim() || null,
      settings,
    })
  }

  const handleDelete = (profile: TuningProfile) => {
    if (profile.is_system) return
    if (!window.confirm(`Delete tuning profile "${profile.name}"?`)) return
    setPendingDeleteId(profile.id)
    deleteMutation.mutate(profile.id)
  }

  const handleApply = () => {
    if (!applyProfile || !selectedMinerId) return
    applyMutation.mutate({
      profileId: applyProfile.id,
      minerId: Number(selectedMinerId),
    })
  }

  const renderProfiles = () => {
    if (profilesQuery.isLoading) {
      return <ProfilesSkeleton />
    }

    if (profilesQuery.isError) {
      return (
        <ErrorState
          message={extractError(profilesQuery.error)}
          onRetry={() => profilesQuery.refetch()}
        />
      )
    }

    const profiles = profilesQuery.data ?? []
    if (profiles.length === 0) {
      return (
        <div className="rounded-2xl border border-dashed border-border/60 bg-muted/5 p-10 text-center text-sm text-muted-foreground">
          No tuning profiles found. Create a profile to get started.
        </div>
      )
    }

    return (
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {profiles.map((profile) => (
          <ProfileCard
            key={profile.id}
            profile={profile}
            onApply={() => {
              setApplyProfile(profile)
              setSelectedMinerId('')
            }}
            onDelete={() => handleDelete(profile)}
            deleteDisabled={profile.is_system || pendingDeleteId === profile.id}
            isDeleting={pendingDeleteId === profile.id && deleteMutation.isPending}
          />
        ))}

        <button
          type="button"
          onClick={() => {
            setCreateOpen(true)
            setFormError(null)
          }}
          className="flex min-h-[220px] flex-col items-center justify-center rounded-2xl border border-dashed border-border/70 bg-muted/5 text-sm text-muted-foreground transition hover:border-blue-500 hover:text-blue-200"
        >
          <Plus className="mb-2 h-6 w-6" />
          Create profile
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-3 text-3xl font-semibold text-foreground">
          <SlidersHorizontal className="h-8 w-8 text-blue-400" />
          <span>Tuning Profiles</span>
        </div>
        <p className="text-base text-muted-foreground">
          Save and reuse safe tuning presets across Avalon Nano, Bitaxe, and NerdQaxe miners. Apply profiles with two clicks and keep your fleet consistent.
        </p>
      </div>

      {banner && (
        <div
          className={cn(
            'rounded-xl border px-4 py-3 text-sm',
            banner.tone === 'success' && 'border-emerald-500/40 bg-emerald-500/10 text-emerald-100',
            banner.tone === 'error' && 'border-red-500/40 bg-red-500/10 text-red-100',
            banner.tone === 'info' && 'border-blue-500/40 bg-blue-500/10 text-blue-100'
          )}
        >
          {banner.message}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Filter profiles</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:max-w-sm">
          <Label className="text-sm text-muted-foreground">Miner type</Label>
          <Select value={filter} onValueChange={(value) => setFilter(value)}>
            <SelectTrigger>
              <SelectValue placeholder="All types" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL_TYPES_VALUE}>All types</SelectItem>
              {MINER_TYPE_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {renderProfiles()}

      <CreateProfileDialog
        open={isCreateOpen}
        onOpenChange={(open) => {
          setCreateOpen(open)
          if (!open) {
            setCreateForm(INITIAL_FORM)
            setFormError(null)
          }
        }}
        form={createForm}
        onFormChange={setCreateForm}
        onSubmit={handleSaveProfile}
        isSubmitting={createMutation.isPending}
        error={formError}
      />

      <ApplyProfileDialog
        profile={applyProfile}
        miners={filteredMiners}
        isLoadingMiners={minersQuery.isFetching}
        selectedMinerId={selectedMinerId}
        onMinerChange={setSelectedMinerId}
        onClose={() => {
          setApplyProfile(null)
          setSelectedMinerId('')
        }}
        onApply={handleApply}
        isApplying={applyMutation.isPending}
      />
    </div>
  )
}

function ProfileCard({
  profile,
  onApply,
  onDelete,
  deleteDisabled,
  isDeleting,
}: {
  profile: TuningProfile
  onApply: () => void
  onDelete: () => void
  deleteDisabled: boolean
  isDeleting: boolean
}) {
  return (
    <Card className="relative h-full border-border/60 bg-muted/5">
      {profile.is_system && (
        <span className="absolute right-4 top-4 rounded-full bg-purple-500/20 px-3 py-1 text-xs font-semibold text-purple-200">
          SYSTEM
        </span>
      )}
      <CardHeader>
        <CardTitle className="space-y-1 text-lg">
          <p className="text-foreground">{profile.name}</p>
          <p className="text-sm text-muted-foreground">{minerTypeLabel(profile.miner_type)}</p>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm text-muted-foreground">
        <p>{profile.description || 'No description provided.'}</p>
        <div className="rounded-xl border border-border/60 bg-background/40 p-3">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Settings</p>
          <dl className="mt-2 space-y-1 text-foreground">
            {Object.entries(profile.settings).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between text-sm">
                <dt className="text-muted-foreground">{formatSettingKey(key)}</dt>
                <dd className="font-medium">{value as string | number}</dd>
              </div>
            ))}
          </dl>
        </div>
      </CardContent>
      <CardFooter className="flex flex-wrap gap-2">
        <Button className="flex-1" onClick={onApply}>
          Apply to miner
        </Button>
        <Button
          type="button"
          variant="ghost"
          disabled={deleteDisabled}
          onClick={onDelete}
          className="flex-1 text-red-400 hover:bg-red-500/10 hover:text-red-200"
        >
          {isDeleting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Trash2 className="mr-2 h-4 w-4" />}
          Delete
        </Button>
      </CardFooter>
    </Card>
  )
}

function minerTypeLabel(type: string) {
  const match = MINER_TYPE_OPTIONS.find((option) => option.value === type)
  return match ? match.label : type
}

function formatSettingKey(key: string) {
  if (key === 'mode') return 'Mode'
  if (key === 'frequency') return 'Frequency (MHz)'
  if (key === 'voltage') return 'Voltage (mV)'
  return key.replace(/_/g, ' ')
}

function CreateProfileDialog({
  open,
  onOpenChange,
  form,
  onFormChange,
  onSubmit,
  isSubmitting,
  error,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  form: CreateProfileForm
  onFormChange: (form: CreateProfileForm) => void
  onSubmit: () => void
  isSubmitting: boolean
  error: string | null
}) {
  const isAvalon = form.minerType === 'avalon_nano'

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto border-border/70 bg-gray-900">
        <DialogHeader>
          <DialogTitle>Create tuning profile</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="profile-name">Profile name</Label>
            <input
              id="profile-name"
              type="text"
              value={form.name}
              onChange={(event) => onFormChange({ ...form, name: event.target.value })}
              className="w-full rounded-lg border border-border/70 bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500/40"
              placeholder="Eco mode, Turbo, etc."
            />
          </div>

          <div className="space-y-2">
            <Label>Miner type</Label>
            <Select
              value={form.minerType}
              onValueChange={(value: MinerType) =>
                onFormChange({
                  ...form,
                  minerType: value,
                  mode: value === 'avalon_nano' ? 'med' : 'standard',
                  frequency: '',
                  voltage: '',
                })
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="Select miner type" />
              </SelectTrigger>
              <SelectContent>
                {MINER_TYPE_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Description (optional)</Label>
            <textarea
              value={form.description}
              onChange={(event) => onFormChange({ ...form, description: event.target.value })}
              className="w-full rounded-lg border border-border/70 bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500/40"
              rows={2}
              placeholder="Explain what this profile is optimized for"
            />
          </div>

          {form.minerType ? (
            <div className="space-y-4 rounded-2xl border border-border/60 bg-muted/5 p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
                <Zap className="h-4 w-4 text-blue-300" /> Tunable settings
              </div>

              <div className="space-y-2">
                <Label>Mode</Label>
                <select
                  value={form.mode}
                  onChange={(event) => onFormChange({ ...form, mode: event.target.value })}
                  className="w-full rounded-lg border border-border/70 bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500/40"
                >
                  {isAvalon ? (
                    <>
                      <option value="low">Low</option>
                      <option value="med">Medium</option>
                      <option value="high">High</option>
                    </>
                  ) : (
                    <>
                      <option value="eco">Eco</option>
                      <option value="standard">Standard</option>
                      <option value="turbo">Turbo</option>
                      <option value="oc">Overclock</option>
                    </>
                  )}
                </select>
              </div>

              {!isAvalon && (
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Frequency (MHz)</Label>
                    <input
                      type="number"
                      value={form.frequency}
                      onChange={(event) => onFormChange({ ...form, frequency: event.target.value })}
                      className="w-full rounded-lg border border-border/70 bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500/40"
                      placeholder="500"
                      min={100}
                      max={1000}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Voltage (mV)</Label>
                    <input
                      type="number"
                      value={form.voltage}
                      onChange={(event) => onFormChange({ ...form, voltage: event.target.value })}
                      className="w-full rounded-lg border border-border/70 bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500/40"
                      placeholder="1200"
                      min={800}
                      max={1500}
                    />
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-border/60 bg-muted/5 p-4 text-sm text-muted-foreground">
              Choose a miner type to reveal the available settings.
            </div>
          )}

          {error && <p className="text-sm text-red-300">{error}</p>}
        </div>

        <DialogFooter className="pt-4">
          <Button variant="secondary" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button onClick={onSubmit} disabled={isSubmitting}>
            {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save profile
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function ApplyProfileDialog({
  profile,
  miners,
  isLoadingMiners,
  selectedMinerId,
  onMinerChange,
  onClose,
  onApply,
  isApplying,
}: {
  profile: TuningProfile | null
  miners: Miner[]
  isLoadingMiners: boolean
  selectedMinerId: string
  onMinerChange: (id: string) => void
  onClose: () => void
  onApply: () => void
  isApplying: boolean
}) {
  return (
    <Dialog open={Boolean(profile)} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="border-border/70 bg-gray-900">
        <DialogHeader>
          <DialogTitle>Apply profile</DialogTitle>
          {profile && (
            <p className="text-sm text-muted-foreground">
              {profile.name} · {minerTypeLabel(profile.miner_type)}
            </p>
          )}
        </DialogHeader>

        {isLoadingMiners ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading compatible miners…
          </div>
        ) : miners.length === 0 ? (
          <p className="text-sm text-muted-foreground">No compatible miners found.</p>
        ) : (
          <div className="space-y-2">
            <Label>Select miner</Label>
            <Select value={selectedMinerId} onValueChange={onMinerChange}>
              <SelectTrigger>
                <SelectValue placeholder="Choose a miner" />
              </SelectTrigger>
              <SelectContent>
                {miners.map((miner) => (
                  <SelectItem key={miner.id} value={String(miner.id)}>
                    {miner.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}

        <DialogFooter className="pt-4">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={onApply} disabled={!selectedMinerId || isApplying || miners.length === 0}>
            {isApplying && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Apply profile
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function ProfilesSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {[...Array(3)].map((_, idx) => (
        <div key={idx} className="space-y-3 rounded-2xl border border-border/40 bg-muted/5 p-6">
          <div className="h-5 w-2/3 animate-pulse rounded bg-muted/30" />
          <div className="h-4 w-1/2 animate-pulse rounded bg-muted/20" />
          <div className="h-20 animate-pulse rounded-xl bg-muted/20" />
          <div className="flex gap-2">
            <div className="h-9 w-full animate-pulse rounded bg-muted/20" />
            <div className="h-9 w-full animate-pulse rounded bg-muted/20" />
          </div>
        </div>
      ))}
    </div>
  )
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="rounded-2xl border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-100">
      <div className="flex items-center gap-2">
        <AlertCircle className="h-4 w-4" /> {message}
      </div>
      <Button variant="secondary" className="mt-3" onClick={onRetry}>
        Retry
      </Button>
    </div>
  )
}
