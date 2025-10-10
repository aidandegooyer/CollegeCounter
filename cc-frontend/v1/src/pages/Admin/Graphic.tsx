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
import { Upload, Download, Palette } from "lucide-react";
import Logo from "@/components/Logo";
import { domToPng } from "modern-screenshot";
import { Spinner } from "@/components/ui/shadcn-io/spinner";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "https://api.collegecounter.org/v1";

function Graphic() {
  const [backgroundImage, setBackgroundImage] = useState<string>("");
  const [seasonFilter, setSeasonFilter] = useState<string | undefined>(
    import.meta.env.VITE_CURRENT_SEASON_ID || undefined,
  );
  const [titleText, setTitleText] = useState("TOP 10 TEAMS");
  const [downloadLoading, setDownloadLoading] = useState(false);
  const [titleColor, setTitleColor] = useState("#ffffff");
  const [teamTextColor, setTeamTextColor] = useState("#ffffff");
  const [backgroundColor, setBackgroundColor] = useState("rgba(0, 0, 0, 0.7)");

  const fileInputRef = useRef<HTMLInputElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Helper function to proxy external images through backend
  const getProxiedImageUrl = (originalUrl: string) => {
    if (!originalUrl) return "";

    // If it's already a data URL or blob, return as-is
    if (originalUrl.startsWith("data:") || originalUrl.startsWith("blob:")) {
      return originalUrl;
    }

    // If it's a local URL, return as-is
    if (
      originalUrl.startsWith("/") ||
      originalUrl.includes(window.location.host)
    ) {
      return originalUrl;
    }
    return `${API_BASE_URL}/proxy/image/?url=${encodeURIComponent(originalUrl)}`;
  };

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
      };
      reader.readAsDataURL(file);
    }
  };

  const clearBackground = () => {
    setBackgroundImage("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const downloadImage = async () => {
    setDownloadLoading(true);
    const graphicElement = document.getElementById("graphic-preview");
    if (!graphicElement) return;

    try {
      // Wait a moment for any proxied images to load
      await new Promise((resolve) => setTimeout(resolve, 1000));

      const dataUrl = await domToPng(graphicElement, {
        width: 900,
        height: 1100,
        scale: 2, // Higher quality (1800x2200px actual size)
        backgroundColor: "#000000",
        style: {
          // Ensure consistent sizing
          transform: "scale(1)",
          transformOrigin: "top left",
        },
        filter: (node) => {
          // Filter out any unwanted elements
          const element = node as Element;
          return !element.classList?.contains("exclude-from-image");
        },
      });

      // Create download link
      const link = document.createElement("a");
      link.download = `college-counter-top-10-${new Date().toISOString().split("T")[0]}.png`;
      link.href = dataUrl;
      link.click();
      setDownloadLoading(false);
    } catch (error) {
      setDownloadLoading(false);
      console.error("Error generating image:", error);

      // Enhanced fallback with visual guide
      const graphicElement = document.getElementById("graphic-preview");
      if (graphicElement) {
        const originalStyle = graphicElement.style.cssText;

        // Add visual guide
        graphicElement.style.outline = "3px dashed #ff0000";
        graphicElement.style.outlineOffset = "5px";
        graphicElement.scrollIntoView({ behavior: "smooth", block: "center" });

        const proceed = confirm(
          "🔴 RED OUTLINE marks the area to screenshot\n\n" +
            "Screenshot failed. Please manually capture:\n\n" +
            "Mac: Press Cmd+Shift+4, then drag to select the red area\n" +
            "Windows: Press Win+Shift+S, then select the red area\n\n" +
            "Click OK when ready, or Cancel to remove the outline.",
        );

        if (!proceed) {
          graphicElement.style.cssText = originalStyle;
        } else {
          setTimeout(() => {
            graphicElement.style.cssText = originalStyle;
          }, 15000);
        }
      }
    }
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
        <h1>Graphic Generator</h1>
        <Button
          onClick={downloadImage}
          className="flex cursor-pointer items-center gap-2"
          disabled={downloadLoading}
        >
          {downloadLoading ? <Spinner /> : <Download className="h-4 w-4" />}
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
            </CardContent>
          </Card>

          {/* Content Controls */}
          <Card className="mb-6">
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
            <CardContent className="flex justify-center">
              <div
                id="graphic-preview"
                className="relative w-full overflow-hidden"
                style={{
                  width: "900px",
                  height: "1100px",
                }}
              >
                {/* Background Image Layer */}
                {backgroundImage ? (
                  <div
                    className="absolute inset-0 z-0"
                    style={{
                      backgroundImage: `url(${backgroundImage})`,
                      backgroundSize: "cover",
                      backgroundPosition: "center",
                      filter: "blur(8px) brightness(75%)",
                    }}
                  />
                ) : (
                  <div
                    className="absolute inset-0 z-0"
                    style={{
                      backgroundColor: "#000000",
                    }}
                  />
                )}

                {/* Content Overlay */}
                <div className="absolute inset-0 z-10 flex flex-col items-center justify-center p-8">
                  {/* Title */}
                  <div
                    className="mb-8 rounded-lg text-center"
                    style={{
                      color: titleColor,
                    }}
                  >
                    <h1 className="font-block text-6xl tracking-wide">
                      {titleText}
                    </h1>
                  </div>

                  {/* Teams List */}
                  <div className="w-150 space-y-2">
                    {topTeams.map((team, index) => (
                      <div
                        key={team.id}
                        className="bg-background flex items-center justify-between rounded-lg border-2 px-4 py-1.5"
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
                              src={getProxiedImageUrl(team.picture)}
                              alt={team.name}
                              className="h-12 w-12 rounded object-cover"
                              crossOrigin="anonymous"
                            />
                          )}
                          <div>
                            <div className="text-2xl font-semibold">
                              {team.name}
                            </div>
                            {team.school_name && (
                              <div className="text-2xl opacity-80">
                                {team.school_name}
                              </div>
                            )}
                          </div>
                        </div>
                        <div className="bg-secondary shadow-secondary/30 rounded-md px-2 py-1 font-mono text-xl shadow-xl">
                          {Math.round(team.elo)}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Footer */}
                  <div
                    className="mt-8 flex items-center"
                    style={{
                      color: teamTextColor,
                    }}
                  >
                    <Logo type="cc" className="h-24 w-24 rounded-md"></Logo>
                    <div className="ml-2">
                      <h1 className="text-5xl!">College</h1>
                      <h1 className="text-5xl!">Counter</h1>
                    </div>
                  </div>
                </div>
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
