import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { usePublicTeams, usePublicSeasons } from "@/services/hooks";
import { Upload, Link, Download, Palette } from "lucide-react";

function Graphic() {
  const [backgroundImage, setBackgroundImage] = useState<string>("");
  const [backgroundUrl, setBackgroundUrl] = useState<string>("");
  const [seasonFilter, setSeasonFilter] = useState<string | undefined>(
    import.meta.env.VITE_CURRENT_SEASON_ID || undefined,
  );
  const [titleText, setTitleText] = useState("TOP 10 TEAMS");
  const [titleColor, setTitleColor] = useState("#ffffff");
  const [teamTextColor, setTeamTextColor] = useState("#ffffff");
  const [backgroundColor, setBackgroundColor] = useState("rgba(0, 0, 0, 0.7)");

  const fileInputRef = useRef<HTMLInputElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Get available seasons
  const { data: seasonsData } = usePublicSeasons({
    sort: "start_date",
    order: "desc",
    page_size: 50,
  });

  // Get top 10 teams
  const { data: teamsData, isLoading } = usePublicTeams({
    sort: "elo",
    order: "desc",
    page_size: 10,
    ...(seasonFilter &&
      seasonFilter !== "all_seasons" && { season_id: seasonFilter }),
  });

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const result = e.target?.result as string;
        setBackgroundImage(result);
        setBackgroundUrl(""); // Clear URL when file is uploaded
      };
      reader.readAsDataURL(file);
    }
  };

  const handleUrlSubmit = () => {
    if (backgroundUrl.trim()) {
      setBackgroundImage(backgroundUrl.trim());
    }
  };

  const clearBackground = () => {
    setBackgroundImage("");
    setBackgroundUrl("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const downloadImage = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // Create a temporary canvas with the graphic content
    const tempCanvas = document.createElement("canvas");
    const tempCtx = tempCanvas.getContext("2d");
    if (!tempCtx) return;

    const graphicElement = document.getElementById("graphic-preview");
    if (!graphicElement) return;

    // Set canvas size to match the graphic
    tempCanvas.width = 1200;
    tempCanvas.height = 800;

    // Use html2canvas alternative - for now, just prompt user to screenshot
    alert(
      'Please use your browser\'s screenshot tool or right-click on the graphic and select "Save image as..." to download the graphic.',
    );
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-gray-900"></div>
      </div>
    );
  }

  const topTeams = teamsData?.results || [];

  return (
    <div className="container mx-auto space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Graphic Generator</h1>
        <Button onClick={downloadImage} className="flex items-center gap-2">
          <Download className="h-4 w-4" />
          Download
        </Button>
      </div>

      <div className="gap-6">
        {/* Controls Panel */}
        <div className="space-y-6">
          {/* Background Controls */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Palette className="h-5 w-5" />
                Background
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* File Upload */}
              <div className="space-y-2">
                <Label htmlFor="background-file">Upload Background Image</Label>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    onClick={() => fileInputRef.current?.click()}
                    className="flex items-center gap-2"
                  >
                    <Upload className="h-4 w-4" />
                    Choose File
                  </Button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    onChange={handleFileUpload}
                    className="hidden"
                  />
                  <Button variant="outline" onClick={clearBackground}>
                    Clear
                  </Button>
                </div>
              </div>

              {/* URL Input */}
              <div className="space-y-2">
                <Label htmlFor="background-url">Or paste image URL</Label>
                <div className="flex gap-2">
                  <Input
                    id="background-url"
                    placeholder="https://example.com/image.jpg"
                    value={backgroundUrl}
                    onChange={(e) => setBackgroundUrl(e.target.value)}
                  />
                  <Button
                    variant="outline"
                    onClick={handleUrlSubmit}
                    className="flex items-center gap-2"
                  >
                    <Link className="h-4 w-4" />
                    Load
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Content Controls */}
          <Card>
            <CardHeader>
              <CardTitle>Content Settings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Season Selection */}
              <div className="space-y-2">
                <Label htmlFor="season">Season</Label>
                <Select value={seasonFilter} onValueChange={setSeasonFilter}>
                  <SelectTrigger id="season">
                    <SelectValue placeholder="Select a season" />
                  </SelectTrigger>
                  <SelectContent>
                    {seasonsData?.results?.map((season) => (
                      <SelectItem key={season.id} value={season.id}>
                        {season.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Title Text */}
              <div className="space-y-2">
                <Label htmlFor="title">Title Text</Label>
                <Input
                  id="title"
                  value={titleText}
                  onChange={(e) => setTitleText(e.target.value)}
                />
              </div>

              {/* Title Color */}
              <div className="space-y-2">
                <Label htmlFor="title-color">Title Color</Label>
                <div className="flex gap-2">
                  <Input
                    id="title-color"
                    type="color"
                    value={titleColor}
                    onChange={(e) => setTitleColor(e.target.value)}
                    className="h-10 w-16 p-1"
                  />
                  <Input
                    value={titleColor}
                    onChange={(e) => setTitleColor(e.target.value)}
                    placeholder="#ffffff"
                  />
                </div>
              </div>

              {/* Team Text Color */}
              <div className="space-y-2">
                <Label htmlFor="team-color">Team Text Color</Label>
                <div className="flex gap-2">
                  <Input
                    id="team-color"
                    type="color"
                    value={teamTextColor}
                    onChange={(e) => setTeamTextColor(e.target.value)}
                    className="h-10 w-16 p-1"
                  />
                  <Input
                    value={teamTextColor}
                    onChange={(e) => setTeamTextColor(e.target.value)}
                    placeholder="#ffffff"
                  />
                </div>
              </div>

              {/* Background Overlay Color */}
              <div className="space-y-2">
                <Label htmlFor="bg-color">Text Background Overlay</Label>
                <Input
                  id="bg-color"
                  value={backgroundColor}
                  onChange={(e) => setBackgroundColor(e.target.value)}
                  placeholder="rgba(0, 0, 0, 0.7)"
                />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Preview Panel */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Preview</CardTitle>
            </CardHeader>
            <CardContent>
              <div
                id="graphic-preview"
                className="relative aspect-[2/3] w-full overflow-hidden rounded-lg border-2 border-dashed border-gray-300"
                style={{
                  backgroundImage: backgroundImage
                    ? `url(${backgroundImage})`
                    : undefined,
                  backgroundSize: "cover",
                  backgroundPosition: "center",
                  backgroundColor: backgroundImage ? undefined : "#f3f4f6",
                }}
              >
                {/* Content Overlay */}
                <div className="absolute inset-0 flex flex-col items-center justify-center p-8">
                  {/* Title */}
                  <div
                    className="mb-8 rounded-lg px-6 py-3 text-center"
                    style={{
                      color: titleColor,
                    }}
                  >
                    <h1 className="font-block text-4xl tracking-wide">
                      {titleText}
                    </h1>
                  </div>

                  {/* Teams List */}
                  <div className="w-150 max-w-md space-y-2">
                    {topTeams.map((team, index) => (
                      <div
                        key={team.id}
                        className="bg-background flex items-center justify-between rounded-lg border-2 px-4 py-3"
                        style={{
                          color: teamTextColor,
                        }}
                      >
                        <div className="flex items-center gap-3">
                          <span className="w-8 text-center text-2xl font-bold">
                            {index + 1}
                          </span>
                          {team.picture && (
                            <img
                              src={team.picture}
                              alt={team.name}
                              className="h-8 w-8 rounded object-cover"
                            />
                          )}
                          <div>
                            <div className="text-xl font-semibold">
                              {team.name}
                            </div>
                            {team.school_name && (
                              <div className="text-2xl opacity-80">
                                {team.school_name}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Footer */}
                  <div
                    className="mt-8 rounded px-4 py-2"
                    style={{
                      backgroundColor: backgroundColor,
                      color: teamTextColor,
                    }}
                  >
                    <p className="text-sm opacity-80">
                      College Counter Rankings
                    </p>
                  </div>
                </div>

                {/* Placeholder when no background */}
                {!backgroundImage && (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <p className="text-lg text-gray-500">
                      Upload or paste a background image
                    </p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Instructions */}
          <Card>
            <CardHeader>
              <CardTitle>How to Save</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 text-sm">
                <p>To save your graphic:</p>
                <ol className="ml-4 list-inside list-decimal space-y-1">
                  <li>Right-click on the preview above</li>
                  <li>
                    Select "Save image as..." or use your browser's screenshot
                    tool
                  </li>
                  <li>Choose your desired location and filename</li>
                </ol>
                <p className="mt-4 text-gray-600">
                  The graphic is optimized for social media sharing (3:2 aspect
                  ratio).
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Hidden canvas for potential future download functionality */}
      <canvas ref={canvasRef} className="hidden" />
    </div>
  );
}

export default Graphic;
