import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertCircle, CheckCircle2 } from "lucide-react";
import { clearDatabase } from "@/services/api";

function ClearDatabase() {
  const [securityKey, setSecurityKey] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);

  const handleClear = async () => {
    if (
      !confirm(
        "Are you sure you want to clear the database? This action cannot be undone!",
      )
    ) {
      return;
    }

    setIsLoading(true);
    setResult(null);

    try {
      const response = await clearDatabase(securityKey);
      setResult({
        success: true,
        message: response.message,
      });
    } catch (error: any) {
      setResult({
        success: false,
        message:
          error.response?.data?.error ||
          "Failed to clear database. Please try again.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Clear Database</CardTitle>
        <CardDescription>
          Clear the database for testing purposes. This will delete all matches,
          participants, teams, players, events, and rankings, but will preserve
          seasons and competitions.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div>
            <Input
              type="password"
              placeholder="Security Key"
              value={securityKey}
              onChange={(e) => setSecurityKey(e.target.value)}
            />
            <p className="mt-1 text-sm text-gray-500">
              Enter the security key to clear the database. Default key is
              "clear_database_for_testing".
            </p>
          </div>

          {result && (
            <Alert variant={result.success ? "default" : "destructive"}>
              {result.success ? (
                <CheckCircle2 className="h-4 w-4" />
              ) : (
                <AlertCircle className="h-4 w-4" />
              )}
              <AlertTitle>{result.success ? "Success" : "Error"}</AlertTitle>
              <AlertDescription>{result.message}</AlertDescription>
            </Alert>
          )}
        </div>
      </CardContent>
      <CardFooter>
        <Button
          variant="destructive"
          onClick={handleClear}
          disabled={isLoading || !securityKey}
        >
          {isLoading ? "Clearing..." : "Clear Database"}
        </Button>
      </CardFooter>
    </Card>
  );
}

export default ClearDatabase;
