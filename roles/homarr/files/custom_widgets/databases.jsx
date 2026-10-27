<SimpleGrid cols={{ base: 3, sm: 6 }} spacing={8} p={8} h="100%">
  {[
    { label: "Postgres size", stat: "pg_size", unit: "bytes", icon: "postgres" },
    { label: "Postgres connections", stat: "pg_connections", unit: "count", icon: "postgres" },
    { label: "Redis memory", stat: "redis_memory", unit: "bytes", icon: "redis" },
    { label: "Redis keys", stat: "redis_keys", unit: "count", icon: "redis" },
    { label: "Redis ops/s", stat: "redis_ops", unit: "rate", icon: "redis" },
    { label: "Redis clients", stat: "redis_clients", unit: "count", icon: "redis" },
  ].map((card) => ({
    ...card,
    value: parseFloat((data.databases?.data?.result ?? []).find((series) => series.metric?.stat === card.stat)?.value?.[1]),
  })).map((card) => (
    <Tooltip key={card.label} label={status.databases?.error || status.databases?.statusText || "Unavailable"} disabled={status.databases?.ok !== false}>
      <Paper radius="md" p="xs" ta="center" style={{ background: "rgb(from var(--mantine-primary-color-filled) r g b / 0.08)", minWidth: 0, minHeight: 104, display: "flex", flexDirection: "column", justifyContent: "center" }}>
        <Group justify="flex-end" h={14}>
          <Image src={`https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/${card.icon}.png`} w={14} h={14} opacity={0.8} />
        </Group>
        <Text fz={26} fw={650} lh={1.2} truncate>
          {status.databases?.ok === false ? "—"
            : isNaN(card.value) ? (status.databases?.loading ? "…" : "—")
            : card.unit === "bytes" ? (card.value >= 1e9 ? `${(card.value / 1e9).toFixed(1)} GB` : `${Math.round(card.value / 1e6)} MB`)
            : card.unit === "rate" ? (card.value >= 10 ? Math.round(card.value).toLocaleString() : card.value.toFixed(1))
            : Math.round(card.value).toLocaleString()}
        </Text>
        <Text fz={11} lh={1.35} opacity={0.7} mt={5}>{card.label}</Text>
      </Paper>
    </Tooltip>
  ))}
</SimpleGrid>
