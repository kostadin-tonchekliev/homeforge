<SimpleGrid cols={{ base: 2, sm: 4 }} spacing={8} p={8} h="100%">
  {[
    { label: "Movies", value: data.jellyfin?.MovieCount, state: status.jellyfin, icon: "jellyfin" },
    { label: "Shows", value: data.jellyfin?.SeriesCount, state: status.jellyfin, icon: "jellyfin" },
    { label: "Episodes", value: data.jellyfin?.EpisodeCount, state: status.jellyfin, icon: "jellyfin" },
    { label: "Kavita series", value: data.kavita?.seriesCount, state: status.kavita, icon: "kavita" },
  ].map((card) => (
    <Tooltip key={card.label} label={card.state?.error || card.state?.statusText || "Unavailable"} disabled={card.state?.ok !== false}>
      <Paper radius="md" p="xs" ta="center" style={{ background: "rgb(from var(--mantine-primary-color-filled) r g b / 0.08)", minWidth: 0, minHeight: 104, display: "flex", flexDirection: "column", justifyContent: "center" }}>
        <Group justify="flex-end" h={14}>
          <Image src={`https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/${card.icon}.png`} w={14} h={14} opacity={0.8} />
        </Group>
        <Text fz={26} fw={650} lh={1.2} truncate>
          {card.state?.ok === false ? "—" : card.value == null ? "…" : card.value.toLocaleString()}
        </Text>
        <Text fz={11} lh={1.35} opacity={0.7} mt={5}>{card.label}</Text>
      </Paper>
    </Tooltip>
  ))}
</SimpleGrid>
