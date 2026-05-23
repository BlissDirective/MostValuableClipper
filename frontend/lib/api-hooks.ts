import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  clipsApi,
  pipelinesApi,
  sourcesApi,
  earningsApi,
  analyticsApi,
  swarmApi,
  agentsApi,
} from './api';

// ─── Batch ────────────────────────────────────────────────────────────────────

export function useBatchJobs(limit: number) {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['batchJobs', limit],
    queryFn: () => swarmApi.getBatchJobs(limit),
    refetchInterval: 5000,
  });
  const raw = data as any;
  return { jobs: raw?.jobs ?? raw ?? [], isLoading, refetch };
}

export function useBatchJob(batchId: string | null) {
  const { data, isLoading } = useQuery({
    queryKey: ['batchJob', batchId],
    queryFn: () => swarmApi.getBatchJob(batchId!),
    enabled: !!batchId,
    refetchInterval: 3000,
  });
  const raw = data as any;
  return {
    job: raw?.job ?? raw ?? null,
    clipResults: raw?.clip_results ?? [],
    isLoading,
  };
}

export function useBatchProgress(batchId: string | null) {
  const { data } = useQuery({
    queryKey: ['batchProgress', batchId],
    queryFn: () => swarmApi.getBatchJob(batchId!),
    enabled: !!batchId,
    refetchInterval: 2000,
  });
  if (!data) return null;
  const job: any = (data as any)?.job ?? data;
  const processed: number = job?.processed_clips ?? 0;
  const total: number = job?.total_clips ?? 1;
  const failed: number = job?.failed_clips ?? 0;
  return {
    current_status: job?.status ?? 'queued',
    processed,
    total,
    failed,
    percent: total > 0 ? Math.round((processed / total) * 100) : 0,
    detail: job?.status === 'running' ? 'Processing clips…' : '',
  };
}

// ─── Swarm execution ──────────────────────────────────────────────────────────

export function useSwarmExecution() {
  const [isRunning, setIsRunning] = useState(false);

  const dispatch = async (fn: () => Promise<any>) => {
    setIsRunning(true);
    try {
      return await fn();
    } finally {
      setIsRunning(false);
    }
  };

  return {
    isRunning,
    runHookSwarm: (clipId: string, platform: string, opts?: Record<string, any>) =>
      dispatch(() => swarmApi.runHooks(clipId, platform, opts)),
    runRemixSwarm: (clipId: string, opts?: Record<string, any>) =>
      dispatch(() => swarmApi.runRemix(clipId, opts)),
    runPostSwarm: (clipIds: string[], opts?: Record<string, any>) =>
      dispatch(() => swarmApi.runPost(clipIds, opts)),
    runABTestSwarm: (clipId: string, variantId: string, opts?: Record<string, any>) =>
      dispatch(() => swarmApi.runABTest(clipId, variantId, opts)),
    runMusicMatchSwarm: (clipId: string, opts?: Record<string, any>) =>
      dispatch(() => swarmApi.runMusicMatch(clipId, opts)),
    runThumbnailSwarm: (clipId: string, opts?: Record<string, any>) =>
      dispatch(() => swarmApi.runThumbnail(clipId, opts)),
    runSafetySwarm: (clipId: string, opts?: Record<string, any>) =>
      dispatch(() => swarmApi.runSafety(clipId, opts)),
    runHooksAnalysisSwarm: (clipId: string, platform: string, opts?: Record<string, any>) =>
      dispatch(() => swarmApi.runHooksAnalysis(clipId, platform, opts)),
    runSegmentAnalyzeSwarm: (clipId: string, opts?: Record<string, any>) =>
      dispatch(() => swarmApi.runSegmentAnalyze(clipId, opts)),
    runEditSwarm: (clipId: string, opts?: Record<string, any>) =>
      dispatch(() => swarmApi.runEdit(clipId, opts)),
  };
}

// ─── Swarm allocation ─────────────────────────────────────────────────────────

export function useSwarmAllocation() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ['swarmAllocation'],
    queryFn: () => swarmApi.getAllocation(),
  });
  const raw = data as any;

  const setAllocation = useMutation({
    mutationFn: (allocation: Record<string, number>) => swarmApi.setAllocation(allocation),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['swarmAllocation'] }),
  });

  const enableAutoBalance = useMutation({
    mutationFn: () => swarmApi.autoBalance(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['swarmAllocation'] }),
  });

  return {
    allocation: raw?.allocation ?? {},
    tier: raw?.tier ?? 'free',
    totalMaxAgents: raw?.total_max_agents ?? 1,
    availableAgents: raw?.available_agents ?? 1,
    autoBalance: raw?.auto_balance ?? true,
    isLoading,
    setAllocation,
    enableAutoBalance,
  };
}

// ─── Swarm batch ──────────────────────────────────────────────────────────────

export function useSwarmBatch() {
  const [isRunning, setIsRunning] = useState(false);

  const runBatch = async (params: {
    clipIds: string[];
    poolType: string;
    agentCount: number;
    strategies: string[];
    priority?: string;
    customOptions?: Record<string, any>;
  }) => {
    setIsRunning(true);
    try {
      return await swarmApi.runBatch({
        clip_ids: params.clipIds,
        pool_type: params.poolType,
        agent_count: params.agentCount,
        strategies: params.strategies,
        priority: params.priority ?? 'balanced',
        ...(params.customOptions ?? {}),
      });
    } finally {
      setIsRunning(false);
    }
  };

  return { isRunning, runBatch };
}

// ─── Swarm config ─────────────────────────────────────────────────────────────

export function useSwarmConfig() {
  const { data, isLoading } = useQuery({
    queryKey: ['swarmConfig'],
    queryFn: () => swarmApi.getConfig(),
  });
  return { config: data ?? null, isLoading };
}

// ─── Clips ────────────────────────────────────────────────────────────────────

export function useClips() {
  const qc = useQueryClient();
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['clips'],
    queryFn: () => clipsApi.getAll(),
  });
  const raw = data as any;

  const approveClip = useMutation({
    mutationFn: (id: string) => clipsApi.approve(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['clips'] }),
  });

  const rejectClip = useMutation({
    mutationFn: (id: string) => clipsApi.reject(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['clips'] }),
  });

  return {
    clips: raw?.clips ?? raw ?? [],
    isLoading,
    refetch,
    approveClip,
    rejectClip,
  };
}

// ─── Pipelines ────────────────────────────────────────────────────────────────

export function usePipelines() {
  const qc = useQueryClient();
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['pipelines'],
    queryFn: () => pipelinesApi.getAll(),
  });
  const raw = data as any;

  const createPipeline = useMutation({
    mutationFn: (params: Record<string, any>) => pipelinesApi.create(params),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipelines'] }),
  });

  const startPipeline = useMutation({
    mutationFn: (id: string) => pipelinesApi.toggle(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipelines'] }),
  });

  const pausePipeline = useMutation({
    mutationFn: (id: string) => pipelinesApi.toggle(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipelines'] }),
  });

  return {
    pipelines: raw?.pipelines ?? raw ?? [],
    isLoading,
    refetch,
    createPipeline,
    startPipeline,
    pausePipeline,
  };
}

// ─── Sources ──────────────────────────────────────────────────────────────────

export function useSources() {
  const qc = useQueryClient();
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['sources'],
    queryFn: () => sourcesApi.getAll(),
  });
  const raw = data as any;

  const createSource = useMutation({
    mutationFn: (params: Record<string, any>) => sourcesApi.create(params),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sources'] }),
  });

  const deleteSource = useMutation({
    mutationFn: (id: string) => sourcesApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sources'] }),
  });

  return {
    sources: raw?.sources ?? raw ?? [],
    isLoading,
    refetch,
    createSource,
    deleteSource,
  };
}

// ─── Earnings ─────────────────────────────────────────────────────────────────

export function useEarnings() {
  const { data, isLoading } = useQuery({
    queryKey: ['earnings'],
    queryFn: () => earningsApi.get(),
  });
  return { earnings: data ?? null, isLoading };
}

// ─── Analytics ────────────────────────────────────────────────────────────────

export function useAnalytics() {
  const { data, isLoading } = useQuery({
    queryKey: ['analytics'],
    queryFn: () => analyticsApi.getDashboard(),
  });
  return { analytics: data ?? null, isLoading };
}

// ─── Content Discovery ──────────────────────────────────────────────────────

export function useDiscoveryStatus(pipelineId: string | null) {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['discoveryStatus', pipelineId],
    queryFn: () => agentsApi.getDiscoveryStatus(pipelineId!),
    enabled: !!pipelineId,
    refetchInterval: 10000,
  });
  return {
    proposals: (data as any)?.proposals ?? [],
    pendingCount: (data as any)?.pending_proposals ?? 0,
    lastDiscoveryRun: (data as any)?.last_discovery_run ?? null,
    isLoading,
    refetch,
  };
}

export function useProposalAction() {
  const qc = useQueryClient();
  const { mutateAsync: action, isPending } = useMutation({
    mutationFn: ({ clipId, action }: { clipId: string; action: 'approve' | 'reject' }) =>
      agentsApi.proposalAction(clipId, action),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['discoveryStatus'] });
      qc.invalidateQueries({ queryKey: ['clips'] });
    },
  });
  return { action, isPending };
}

export function useAgentSources(pipelineId: string | null) {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['agentSources', pipelineId],
    queryFn: () => agentsApi.getSources(pipelineId!),
    enabled: !!pipelineId,
  });
  return {
    sources: (data as any)?.sources ?? [],
    total: (data as any)?.total ?? 0,
    isLoading,
    refetch,
  };
}

export function useAgentStatus() {
  const { data, isLoading } = useQuery({
    queryKey: ['agentStatus'],
    queryFn: () => agentsApi.getAgentStatus(),
    refetchInterval: 30000,
  });
  return { status: data ?? null, isLoading };
}
