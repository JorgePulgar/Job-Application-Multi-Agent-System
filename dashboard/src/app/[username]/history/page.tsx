export default async function HistoryPage({
  params,
}: {
  params: Promise<{ username: string }>;
}) {
  const { username } = await params;
  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">Historial</h1>
      <p className="text-muted-foreground text-sm">
        Usuario: <strong>{username}</strong> — página pendiente (Task 06).
      </p>
    </div>
  );
}
