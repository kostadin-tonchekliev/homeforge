<Stack p={8} h="100%">
  {[{
    free: parseFloat((data.disk?.data?.result ?? []).find((series) => series.metric?.stat === "free")?.value?.[1]),
    size: parseFloat((data.disk?.data?.result ?? []).find((series) => series.metric?.stat === "size")?.value?.[1]),
  }].map((disk) => ({ ...disk, used: 100 * (1 - disk.free / disk.size) })).map((disk) => (
    <Tooltip key="disk" label={status.disk?.error || status.disk?.statusText || "Unavailable"} disabled={status.disk?.ok !== false}>
      <Paper radius="md" p="xs" ta="center" style={{ background: "rgb(from var(--mantine-primary-color-filled) r g b / 0.08)", minWidth: 0, minHeight: 104, flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
        <Group justify="flex-end" h={14}>
          <Image src="https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/prometheus.png" w={14} h={14} opacity={0.8} />
        </Group>
        <Text fz={26} fw={650} lh={1.2} truncate c={disk.used >= 90 ? "red" : disk.used >= 80 ? "orange" : undefined}>
          {status.disk?.ok === false || isNaN(disk.free) ? (status.disk?.loading ? "…" : "—")
            : disk.free >= 100e9 ? `${Math.round(disk.free / 1e9)} GB` : `${(disk.free / 1e9).toFixed(1)} GB`}
        </Text>
        {!isNaN(disk.used) && (
          <Progress value={disk.used} color={disk.used >= 90 ? "red" : disk.used >= 80 ? "orange" : "green"} size="sm" radius="xl" mt={6} />
        )}
        <Text fz={11} lh={1.35} opacity={0.7} mt={5} truncate>
          {isNaN(disk.used) ? "Free on /media" : `Free on /media · ${Math.round(disk.used)}% of ${(disk.size / 1e12).toFixed(1)} TB used`}
        </Text>
      </Paper>
    </Tooltip>
  ))}
</Stack>
