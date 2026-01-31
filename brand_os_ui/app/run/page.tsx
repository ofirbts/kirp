import RunForm from "@/components/RunForm";

export default function RunPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold text-primary">Run pipeline</h1>
      <p className="mt-2 text-neutral-200">Trigger POST /brand-os/run with tenant, platform, and topic.</p>
      <div className="mt-6">
        <RunForm />
      </div>
    </div>
  );
}
