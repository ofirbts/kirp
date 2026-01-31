import Link from "next/link";

export default function Home() {
  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold text-primary">Brand OS v3</h1>
      <p className="mt-2 text-neutral-200">Run the pipeline, view history, agents, and visuals.</p>
      <div className="mt-6 flex gap-4">
        <Link href="/dashboard" className="bg-primary text-white px-4 py-2 rounded hover:bg-primary/90">
          Dashboard
        </Link>
        <Link href="/run" className="bg-secondary text-primary px-4 py-2 rounded hover:bg-secondary/90">
          Run
        </Link>
      </div>
    </div>
  );
}
