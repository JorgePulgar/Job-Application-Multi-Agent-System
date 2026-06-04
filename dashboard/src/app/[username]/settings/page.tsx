export default async function SettingsPage({
  params,
}: {
  params: Promise<{ username: string }>;
}) {
  const { username } = await params;
  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">Ajustes</h1>
      <p className="text-muted-foreground text-sm">
        Usuario: <strong>{username}</strong> — página pendiente (Task 07).
      </p>
    </div>
  );
}
