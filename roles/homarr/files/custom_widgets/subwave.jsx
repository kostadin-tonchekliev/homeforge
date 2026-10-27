<Stack p={8} h="100%">
  <Tooltip label={status.now?.error || status.now?.statusText || "Unavailable"} disabled={status.now?.ok !== false}>
    <Paper radius="md" p="xs" style={{ background: "rgb(from var(--mantine-primary-color-filled) r g b / 0.08)", minWidth: 0, minHeight: 104, flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
      <Group justify="space-between" wrap="nowrap" h={14}>
        <Group gap={6} wrap="nowrap" style={{ minWidth: 0 }}>
          <Box w={8} h={8} style={{ borderRadius: "50%", flexShrink: 0, background: data.now?.streamOnline ? "var(--mantine-color-green-6)" : "var(--mantine-color-red-6)" }} />
          <Text fz={11} lh={1.35} opacity={0.7} truncate>
            {status.now?.ok === false ? "Station unavailable"
              : data.now == null ? "…"
              : `${data.now.streamOnline ? "On air" : "Off air"} · ${data.now.listeners?.current ?? 0} listening`}
          </Text>
        </Group>
        <Image src={`${options.station_url}/icons/192`} w={14} h={14} opacity={0.8} />
      </Group>
      <Group gap="sm" wrap="nowrap" mt={8}>
        {data.now?.nowPlaying?.subsonic_id && (
          <Image src={`${options.station_url}/api/cover/${data.now.nowPlaying.subsonic_id}`} w={56} h={56} radius="sm" style={{ flexShrink: 0 }} />
        )}
        <Stack gap={2} style={{ minWidth: 0 }}>
          <Text fz={15} fw={650} lh={1.25} truncate>{data.now?.nowPlaying?.title || "Nothing playing"}</Text>
          <Text fz={12} lh={1.3} opacity={0.7} truncate>{data.now?.nowPlaying?.artist || ""}</Text>
          <Text fz={11} lh={1.3} opacity={0.6} truncate>
            {data.now?.dj?.name ? `DJ ${data.now.dj.name}${data.now.activeShow?.name ? ` · ${data.now.activeShow.name}` : ""}` : ""}
          </Text>
        </Stack>
      </Group>
    </Paper>
  </Tooltip>
</Stack>
