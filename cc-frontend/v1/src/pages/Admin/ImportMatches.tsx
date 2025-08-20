import { useState, useEffect } from "react";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertCircle, CheckCircle2 } from "lucide-react";
import {
  fetchSeasons,
  createSeason,
  importMatches,
  fetchFaceitMatches,
  fetchPlayflyMatches,
} from "@/services/api";

import type { Season } from "@/services/api";

function SelectPlatform({
  platform,
  setPlatform,
}: {
  platform: string;
  setPlatform: (platform: string) => void;
}) {
  return (
    <div className="mb-8 flex flex-col items-center justify-center space-y-4">
      <h1 className="text-3xl">Select Platform</h1>
      <RadioGroup value={platform} onValueChange={setPlatform}>
        <div className="flex items-center space-x-2">
          <RadioGroupItem value="faceit" id="faceit" />
          <Label htmlFor="faceit">Faceit</Label>
        </div>
        <div className="flex items-center space-x-2">
          <RadioGroupItem value="playfly" id="playfly" />
          <Label htmlFor="playfly">Playfly</Label>
        </div>
      </RadioGroup>
    </div>
  );
}

function SelectLeagueOrEvent({
  eventType,
  setEventType,
}: {
  eventType: string;
  setEventType: (type: string) => void;
}) {
  return (
    <div className="mb-8 flex flex-col items-center justify-center space-y-4">
      <h1 className="text-3xl">Select Type</h1>
      <RadioGroup value={eventType} onValueChange={setEventType}>
        <div className="flex items-center space-x-2">
          <RadioGroupItem value="event" id="event" />
          <Label htmlFor="event">Event (Bracket based)</Label>
        </div>
        <div className="flex items-center space-x-2">
          <RadioGroupItem value="league" id="league" />
          <Label htmlFor="league">League</Label>
        </div>
      </RadioGroup>
    </div>
  );
}

function SelectOrCreateSeason({
  seasons,
  selectedSeason,
  setSelectedSeason,
  setShowCreateSeason,
}: {
  seasons: Season[];
  selectedSeason: string;
  setSelectedSeason: (seasonId: string) => void;
  setShowCreateSeason: (show: boolean) => void;
}) {
  return (
    <div className="mb-8 flex flex-col items-center justify-center space-y-4">
      <h1 className="text-3xl">Select Season</h1>
      <Select value={selectedSeason} onValueChange={setSelectedSeason}>
        <SelectTrigger className="w-[180px]">
          <SelectValue placeholder="Season" />
        </SelectTrigger>
        <SelectContent>
          {(Array.isArray(seasons) ? seasons : []).map((season) => (
            <SelectItem key={season.id} value={season.id}>
              {season.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Button variant="outline" onClick={() => setShowCreateSeason(true)}>
        Create New Season
      </Button>
    </div>
  );
}

function CreateSeasonForm({
  onCancel,
  onSuccess,
}: {
  onCancel: () => void;
  onSuccess: (season: Season) => void;
}) {
  const [name, setName] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      const newSeason = await createSeason(name, startDate, endDate);
      onSuccess(newSeason);
    } catch (err: any) {
      setError(err.response?.data?.error || "Failed to create season");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="mb-8 flex flex-col items-center justify-center space-y-4">
      <h1 className="text-3xl">Create New Season</h1>
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <form onSubmit={handleSubmit} className="w-full max-w-md space-y-4">
        <div>
          <Label htmlFor="name">Season Name</Label>
          <Input
            id="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>
        <div>
          <Label htmlFor="startDate">Start Date</Label>
          <Input
            id="startDate"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            required
          />
        </div>
        <div>
          <Label htmlFor="endDate">End Date</Label>
          <Input
            id="endDate"
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            required
          />
        </div>
        <div className="flex justify-end space-x-2">
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" disabled={isLoading}>
            {isLoading ? "Creating..." : "Create Season"}
          </Button>
        </div>
      </form>
    </div>
  );
}

function MetadataForm({
  competitionName,
  setCompetitionName,
  eventId,
  setEventId,
  platform,
}: {
  competitionName: string;
  setCompetitionName: (name: string) => void;
  eventId: string;
  setEventId: (id: string) => void;
  platform: string;
}) {
  return (
    <div className="mb-8 flex flex-col items-center justify-center space-y-4">
      <h1 className="text-3xl">Input Data</h1>
      <div className="w-full max-w-md space-y-4">
        <div>
          <Label htmlFor="competitionName">Competition Name</Label>
          <Input
            id="competitionName"
            value={competitionName}
            onChange={(e) => setCompetitionName(e.target.value)}
            placeholder="Competition Name"
            className="max-w-xl"
          />
        </div>
        <div>
          <Label htmlFor="eventId">
            {platform === "faceit"
              ? "Faceit Championship ID"
              : "Playfly Event ID"}
          </Label>
          <Input
            id="eventId"
            value={eventId}
            onChange={(e) => setEventId(e.target.value)}
            placeholder={
              platform === "faceit"
                ? "Faceit Championship ID"
                : "Playfly Event ID"
            }
            className="max-w-xl"
          />
        </div>
      </div>
    </div>
  );
}

function ImportPreview({
  previewData,
  isLoading,
}: {
  previewData: any;
  isLoading: boolean;
}) {
  if (isLoading) {
    return (
      <div className="mb-8 flex flex-col items-center justify-center space-y-4">
        <h1 className="text-3xl">Loading Preview...</h1>
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-blue-500 border-t-transparent"></div>
      </div>
    );
  }

  if (!previewData) {
    return (
      <div className="mb-8 flex flex-col items-center justify-center space-y-4">
        <h1 className="text-3xl">Import Preview</h1>
        <p>No data available for preview</p>
      </div>
    );
  }

  // For Faceit data
  const matches = previewData.items || [];

  return (
    <div className="mb-8 flex flex-col items-center justify-center space-y-4">
      <h1 className="text-3xl">Import Preview</h1>
      <div className="w-full max-w-2xl">
        <p>Found {matches.length} matches to import</p>
        <div className="mt-4 max-h-80 overflow-y-auto rounded border p-4">
          {matches.map((match: any, index: number) => {
            const team1Key = Object.keys(match.teams)[0];
            const team2Key = Object.keys(match.teams)[1];
            const team1 = match.teams[team1Key];
            const team2 = match.teams[team2Key];

            return (
              <div key={match.match_id || index} className="mb-2 border-b p-2">
                <p className="font-semibold">
                  {team1?.name || "Team 1"} vs {team2?.name || "Team 2"}
                </p>
                <p className="text-sm">Status: {match.status}</p>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function ParticipantMatcher() {
  return (
    <div className="mb-8 flex flex-col items-center justify-center space-y-4">
      <h1 className="text-3xl">Participant Matcher</h1>
      <p>This feature will be implemented later</p>
    </div>
  );
}

function ImportMatches() {
  // State for multi-step form
  const [step, setStep] = useState(0);
  const [platform, setPlatform] = useState("faceit");
  const [eventType, setEventType] = useState("event");
  const [seasons, setSeasons] = useState<Season[]>([]);
  const [selectedSeason, setSelectedSeason] = useState("");
  const [showCreateSeason, setShowCreateSeason] = useState(false);
  const [competitionName, setCompetitionName] = useState("");
  const [eventId, setEventId] = useState("");
  const [previewData, setPreviewData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [importStatus, setImportStatus] = useState<{
    success?: boolean;
    message?: string;
  }>({});

  // Fetch seasons on component mount
  useEffect(() => {
    const getSeasons = async () => {
      try {
        const seasonsData = await fetchSeasons();
        setSeasons(seasonsData);
        if (seasonsData.length > 0) {
          setSelectedSeason(seasonsData[0].id);
        }
      } catch (error) {
        console.error("Failed to fetch seasons:", error);
      }
    };

    getSeasons();
  }, []);

  const handleNewSeason = (newSeason: Season) => {
    setSeasons([...seasons, newSeason]);
    setSelectedSeason(newSeason.id);
    setShowCreateSeason(false);
  };

  const nextStep = async () => {
    // Validate current step
    if (step === 2 && !selectedSeason) {
      alert("Please select a season");
      return;
    }

    if (step === 3 && (!competitionName || !eventId)) {
      alert("Please fill in all fields");
      return;
    }

    // Special handling for preview step
    if (step === 3) {
      setIsLoading(true);
      try {
        let data;
        if (platform === "faceit") {
          data = await fetchFaceitMatches(eventId);
        } else {
          data = await fetchPlayflyMatches(eventId);
        }
        setPreviewData(data);
      } catch (error) {
        console.error("Failed to fetch preview data:", error);
        alert(
          "Failed to fetch preview data. Please check the event ID and try again.",
        );
        setIsLoading(false);
        return;
      }
      setIsLoading(false);
    }

    // Special handling for import step
    if (step === 4) {
      setIsLoading(true);
      try {
        const result = await importMatches({
          platform: platform as "faceit" | "playfly",
          competition_name: competitionName,
          season_id: selectedSeason,
          data: previewData,
        });

        setImportStatus({
          success: true,
          message: `Successfully imported ${result.matches_imported} matches!`,
        });
      } catch (error: any) {
        console.error("Import failed:", error);
        setImportStatus({
          success: false,
          message:
            error.response?.data?.error || "Import failed. Please try again.",
        });
      }
      setIsLoading(false);
    }

    setStep((prev) => Math.min(prev + 1, 5));
  };

  const prevStep = () => {
    setStep((prev) => Math.max(prev - 1, 0));
  };

  // Render current step
  const renderStep = () => {
    if (showCreateSeason) {
      return (
        <CreateSeasonForm
          onCancel={() => setShowCreateSeason(false)}
          onSuccess={handleNewSeason}
        />
      );
    }

    switch (step) {
      case 0:
        return <SelectPlatform platform={platform} setPlatform={setPlatform} />;
      case 1:
        return (
          <SelectLeagueOrEvent
            eventType={eventType}
            setEventType={setEventType}
          />
        );
      case 2:
        return (
          <SelectOrCreateSeason
            seasons={seasons}
            selectedSeason={selectedSeason}
            setSelectedSeason={setSelectedSeason}
            setShowCreateSeason={setShowCreateSeason}
          />
        );
      case 3:
        return (
          <MetadataForm
            competitionName={competitionName}
            setCompetitionName={setCompetitionName}
            eventId={eventId}
            setEventId={setEventId}
            platform={platform}
          />
        );
      case 4:
        return (
          <ImportPreview previewData={previewData} isLoading={isLoading} />
        );
      case 5:
        return <ParticipantMatcher />;
      default:
        return null;
    }
  };

  return (
    <div className="flex justify-center">
      <div className="w-full max-w-[600px]">
        <h1 className="mb-8 text-2xl font-bold">Import Matches</h1>

        {/* Progress indicator */}
        <div className="mb-8">
          <div className="flex justify-between">
            {["Platform", "Type", "Season", "Details", "Preview", "Match"].map(
              (label, index) => (
                <div
                  key={label}
                  className={`flex flex-col items-center ${index <= step ? "text-primary" : "text-muted-foreground"}`}
                >
                  <div
                    className={`mb-1 flex h-6 w-6 items-center justify-center rounded-full ${
                      index < step
                        ? "bg-primary text-white"
                        : index === step
                          ? "border-primary border-2"
                          : "border-muted border-2"
                    }`}
                  >
                    {index < step ? "✓" : ""}
                  </div>
                  <span className="text-xs">{label}</span>
                </div>
              ),
            )}
          </div>
          <div className="bg-muted mt-2 h-1">
            <div
              className="bg-primary h-full transition-all"
              style={{ width: `${(step / 5) * 100}%` }}
            ></div>
          </div>
        </div>

        {importStatus.message && (
          <Alert
            variant={importStatus.success ? "default" : "destructive"}
            className="mb-4"
          >
            {importStatus.success ? (
              <CheckCircle2 className="h-4 w-4" />
            ) : (
              <AlertCircle className="h-4 w-4" />
            )}
            <AlertTitle>
              {importStatus.success ? "Success" : "Error"}
            </AlertTitle>
            <AlertDescription>{importStatus.message}</AlertDescription>
          </Alert>
        )}

        {renderStep()}

        <div className="mt-8 flex justify-between">
          {step > 0 && (
            <button
              className="cursor-pointer rounded-md bg-gray-300 p-2 px-4 text-gray-800 transition-all duration-300 hover:bg-gray-400"
              onClick={prevStep}
              disabled={isLoading}
            >
              Previous
            </button>
          )}
          <div className="flex-1"></div>
          <button
            className="bg-primary cursor-pointer rounded-md p-2 px-4 text-white transition-all duration-300 hover:bg-[#b5670b]"
            onClick={nextStep}
            disabled={isLoading}
          >
            {isLoading ? "Loading..." : step === 4 ? "Import" : "Next"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ImportMatches;
