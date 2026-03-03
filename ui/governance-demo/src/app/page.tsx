import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-50 text-zinc-900 dark:bg-zinc-950 dark:text-zinc-100 flex items-center justify-center px-8">
      <Link
        href="/demo"
        className="rounded-lg bg-blue-600 px-5 py-3 text-white hover:bg-blue-500 transition-colors"
      >
        Open Governance Demo
      </Link>
    </main>
  );
}
