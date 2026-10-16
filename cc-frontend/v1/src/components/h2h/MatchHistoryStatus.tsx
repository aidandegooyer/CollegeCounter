import { Spinner } from "@/components/ui/shadcn-io/spinner";

// Loading / error placeholder shared by the match history components
export function MatchHistoryStatus({
  isLoading,
  error,
}: {
  isLoading: boolean;
  error: unknown;
}) {
  if (isLoading) {
    return (
      <div className="flex justify-center py-4">
        <Spinner />
      </div>
    );
  }
  if (error) {
    return (
      <div className="text-destructive">
        Failed to load match history. Please try again later.
      </div>
    );
  }
  return null;
}
