<SimpleGrid cols={{ base: 3, sm: 6 }} spacing={8} p={8} h="100%">
  {[
    { label: "CPU", stat: "cpu", unit: "percent" },
    { label: "Memory", stat: "memory", unit: "percent" },
    { label: "System disk", stat: "system_disk", unit: "percent" },
    { label: "Uptime", stat: "uptime", unit: "seconds" },
    { label: "Targets up", stat: "targets_up", unit: "count" },
    { label: "Targets down", stat: "targets_down", unit: "count", warn: true },
  ].map((card) => ({
    ...card,
    value: parseFloat((data.server?.data?.result ?? []).find((series) => series.metric?.stat === card.stat)?.value?.[1]),
  })).map((card) => (
    <Tooltip key={card.label} label={status.server?.error || status.server?.statusText || "Unavailable"} disabled={status.server?.ok !== false}>
      <Paper radius="md" p="xs" ta="center" style={{ background: "rgb(from var(--mantine-primary-color-filled) r g b / 0.08)", minWidth: 0, minHeight: 104, display: "flex", flexDirection: "column", justifyContent: "center" }}>
        <Group justify="flex-end" h={14}>
          <Image src="https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/prometheus.png" w={14} h={14} opacity={0.8} />
        </Group>
        <Text fz={26} fw={650} lh={1.2} truncate c={card.warn && card.value > 0 ? "red" : card.unit === "percent" && card.value >= 90 ? "red" : card.unit === "percent" && card.value >= 80 ? "orange" : undefined}>
          {status.server?.ok === false ? "—"
            : isNaN(card.value) ? (status.server?.loading ? "…" : "—")
            : card.unit === "percent" ? `${Math.round(card.value)}%`
            : card.unit === "count" ? card.value.toLocaleString()
            : card.value >= 86400 ? `${Math.floor(card.value / 86400)} d`
            : card.value >= 3600 ? `${Math.floor(card.value / 3600)} h`
            : `${Math.floor(card.value / 60)} min`}
        </Text>
        <Text fz={11} lh={1.35} opacity={0.7} mt={5}>{card.label}</Text>
      </Paper>
    </Tooltip>
  ))}
</SimpleGrid>
