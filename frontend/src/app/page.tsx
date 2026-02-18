import { IdeaForm } from "@/components/idea-form";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-6 pt-16">
      <div className="w-full max-w-3xl text-center">
        {/* hero */}
        <h1 className="font-display text-5xl font-bold tracking-tight sm:text-7xl">
          validate your{" "}
          <span className="inline-flex flex-col">
            <span>idea</span>
            <span className="cursor-blink h-1.5 sm:h-2 w-full rounded-full bg-build -mt-1"></span>
          </span>
        </h1>
        <p className="mt-6 text-lg text-muted">
          stop guessing. know if your idea is worth building
          before you waste your time on it.
        </p>

        {/* form */}
        <div className="mt-12">
          <IdeaForm />
        </div>

        {/* subtle bottom tag */}
        <p className="mt-16 text-xs text-muted/40">
          powered by anthropic
        </p>
      </div>
    </div>
  );
}
