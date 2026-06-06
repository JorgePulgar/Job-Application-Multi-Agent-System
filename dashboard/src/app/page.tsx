import { UserPicker } from "@/components/user-picker";

export default function HomePage() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 p-8">
      <h1 className="text-3xl font-bold tracking-tight">Job Agent</h1>
      <UserPicker />
    </main>
  );
}
