<SimpleGrid cols={{ base: 3, sm: 6 }} spacing={8} p={8} h="100%">
  {[
    { label: "Running", value: (data.stats ?? []).reduce((sum, environment) => sum + (environment.containers?.running ?? 0), 0) },
    { label: "Stopped", value: (data.stats ?? []).reduce((sum, environment) => sum + (environment.containers?.stopped ?? (environment.containers?.total ?? 0) - (environment.containers?.running ?? 0)), 0), warn: true },
    { label: "Updates available", value: (data.stats ?? []).reduce((sum, environment) => sum + (environment.containers?.pendingUpdates ?? 0), 0), warn: true },
    { label: "Images", value: (data.stats ?? []).reduce((sum, environment) => sum + (environment.images?.total ?? 0), 0) },
    { label: "Volumes", value: (data.stats ?? []).reduce((sum, environment) => sum + (environment.volumes?.total ?? 0), 0) },
    { label: "Stacks running", text: `${(data.stats ?? []).reduce((sum, environment) => sum + (environment.stacks?.running ?? 0), 0)} / ${(data.stats ?? []).reduce((sum, environment) => sum + (environment.stacks?.total ?? 0), 0)}` },
  ].map((card) => (
    <Tooltip key={card.label} label={status.stats?.error || status.stats?.statusText || "Unavailable"} disabled={status.stats?.ok !== false}>
      <Paper radius="md" p="xs" ta="center" style={{ background: "rgb(from var(--mantine-primary-color-filled) r g b / 0.08)", minWidth: 0, minHeight: 104, display: "flex", flexDirection: "column", justifyContent: "center" }}>
        <Group justify="flex-end" h={14}>
          <Image src="https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/dockhand.png" w={14} h={14} opacity={0.8} />
        </Group>
        <Text fz={26} fw={650} lh={1.2} truncate c={card.warn && card.value > 0 ? "orange" : undefined}>
          {status.stats?.ok === false ? "—" : data.stats == null ? "…" : card.text ?? card.value.toLocaleString()}
        </Text>
        <Text fz={11} lh={1.35} opacity={0.7} mt={5}>{card.label}</Text>
      </Paper>
    </Tooltip>
  ))}
</SimpleGrid>
