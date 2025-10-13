import { useParams, useNavigate } from "react-router";
import { Spinner } from "@/components/ui/shadcn-io/spinner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  CalendarDays,
  MapPin,
  Trophy,
  Users,
  ExternalLink,
  Twitch,
  MessageCircle,
  ArrowLeft,
  DollarSign,
  FileText,
} from "lucide-react";
import { usePublicEvent } from "@/services/hooks";

import c4_logo from "@/assets/c4 title.svg";
import type { PublicEvent } from "@/services/api";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TabsContent } from "@radix-ui/react-tabs";
import { CountdownTimer } from "@/components/CountdownTimer";

// Simple Badge component (reused from Events.tsx)
function Badge({
  variant = "default",
  className = "",
  children,
}: {
  variant?: "default" | "secondary" | "destructive" | "outline";
  className?: string;
  children: React.ReactNode;
}) {
  const baseStyles =
    "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold";
  const variantStyles = {
    default: "bg-primary text-primary-foreground",
    secondary: "bg-secondary text-secondary-foreground",
    destructive: "bg-destructive text-destructive-foreground",
    outline: "border border-input bg-background text-foreground",
  };

  return (
    <span className={`${baseStyles} ${variantStyles[variant]} ${className}`}>
      {children}
    </span>
  );
}

export function Event() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: event, isLoading, error } = usePublicEvent(id!);

  const formatDate = (date: Date) => {
    return date.toLocaleDateString("en-US", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
  };

  const formatDateTime = (dateString: string) => {
    const date = new Date(dateString);
    return {
      date: formatDate(date),
      time: formatTime(date),
      full: date,
    };
  };

  if (isLoading) {
    return (
      <div className="app-container mx-4 flex justify-center">
        <div className="w-full max-w-[1200px]">
          <div className="flex h-64 items-center justify-center">
            <Spinner className="h-8 w-8" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !event) {
    return (
      <div className="app-container mx-4 flex justify-center">
        <div className="w-full max-w-[1200px]">
          <Button
            variant="ghost"
            onClick={() => navigate("/events")}
            className="mb-6"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Events
          </Button>

          <div className="flex h-64 flex-col items-center justify-center text-center">
            <Trophy className="text-muted-foreground mb-3 h-12 w-12" />
            <h3 className="mb-2 text-lg font-semibold">Event Not Found</h3>
            <p className="text-muted-foreground mb-4">
              {error?.message ||
                "The event you're looking for doesn't exist or has been removed."}
            </p>
            <Button onClick={() => navigate("/events")}>
              Browse All Events
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const startDateTime = formatDateTime(event.start_date);

  return (
    <div className="app-container mx-4 flex justify-center">
      <div className="mx-6 w-full max-w-[1200px] space-y-6">
        {/* Back Button */}
        <Button
          variant="ghost"
          onClick={() => navigate("/events")}
          className="mb-6 cursor-pointer"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Events
        </Button>

        {/* Hero Section */}
        <div className="grid grid-cols-1 gap-6 md:grid md:grid-cols-3">
          <div className="relative col-span-2">
            {event.picture && (
              <div className="h-64 w-full overflow-hidden rounded-lg bg-gradient-to-r from-blue-500 to-purple-600 md:h-80">
                <img
                  src={event.picture}
                  alt={event.name}
                  className="h-full w-full object-cover"
                />
                <div className="absolute inset-0 bg-black bg-opacity-40" />
              </div>
            )}
            <div
              className={`${event.picture ? "absolute bottom-0 left-0 right-0 p-6 text-white" : ""}`}
            >
              {event.custom_details?.is_featured ? (
                <img src={c4_logo} alt="C4 Logo" className="mb-2 h-24 w-auto" />
              ) : (
                <h1>{event.name}</h1>
              )}
              {event.winner && (
                <div className="mb-2 flex items-center gap-2">
                  <Trophy className="h-5 w-5 text-yellow-500" />
                  <span className="text-lg font-medium">
                    Winner: {event.winner.name}
                  </span>
                </div>
              )}
            </div>
          </div>
          <div className="hidden md:flex md:items-center md:justify-center">
            <CountdownTimer targetDate={startDateTime.full} />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Main Content */}
          <div className="space-y-6 lg:col-span-2">
            {event.custom_details && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                  {event.custom_details.prize_pool && (
                    <div className="flex items-center gap-3 rounded-lg bg-yellow-50 p-3 dark:bg-yellow-950/20">
                      <Trophy className="h-5 w-5 text-yellow-600" />
                      <div>
                        <p className="font-medium">Prize Pool</p>
                        <p className="text-muted-foreground text-sm">
                          {event.custom_details.prize_currency}{" "}
                          {event.custom_details.prize_pool}
                        </p>
                      </div>
                    </div>
                  )}

                  {event.custom_details.max_teams && (
                    <div className="flex items-center gap-3 rounded-lg bg-blue-50 p-3 dark:bg-blue-950/20">
                      <Users className="h-5 w-5 text-blue-600" />
                      <div>
                        <p className="font-medium">Max Teams</p>
                        <p className="text-muted-foreground text-sm">
                          {event.custom_details.max_teams} teams
                        </p>
                      </div>
                    </div>
                  )}

                  {event.custom_details.entry_fee &&
                    parseFloat(event.custom_details.entry_fee) > 0 && (
                      <div className="flex items-center gap-3 rounded-lg bg-green-50 p-3 dark:bg-green-950/20">
                        <DollarSign className="h-5 w-5 text-green-600" />
                        <div>
                          <p className="font-medium">Entry Fee</p>
                          <p className="text-muted-foreground text-sm">
                            {event.custom_details.prize_currency}{" "}
                            {event.custom_details.entry_fee}
                          </p>
                        </div>
                      </div>
                    )}

                  {event.custom_details.format && (
                    <div className="flex items-center gap-3 rounded-lg bg-purple-50 p-3 dark:bg-purple-950/20">
                      <MapPin className="h-5 w-5 text-purple-600" />
                      <div>
                        <p className="font-medium">Format</p>
                        <p className="text-muted-foreground text-sm">
                          {event.custom_details.format}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {MainContentSwitcher(event)}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Event Schedule */}
            <Card className="bg-background">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CalendarDays className="h-5 w-5" />
                  Schedule
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="mb-1 font-medium">Event Start</p>
                  <p className="text-sm">{startDateTime.date}</p>
                  <p className="text-muted-foreground text-sm">
                    {startDateTime.time}
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Registration Status */}
            {event.custom_details &&
              (event.custom_details.registration_open ? (
                <div>
                  <div className="rounded-lg bg-green-50 p-3 dark:bg-green-950/20">
                    <p className="mb-1 font-medium text-green-800 dark:text-green-100">
                      Registration Open
                    </p>
                    <p className="text-sm text-green-600 dark:text-green-300">
                      Sign up now to secure your spot!
                    </p>
                  </div>
                  {event.custom_details.registration_link &&
                    event.custom_details.registration_open && (
                      <Button asChild className="mt-2 w-full">
                        <a
                          href={event.custom_details.registration_link}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          Register Now
                          <ExternalLink className="ml-2 h-4 w-4" />
                        </a>
                      </Button>
                    )}
                </div>
              ) : (
                <div className="rounded-lg bg-red-50 p-3 dark:bg-red-950/20">
                  <p className="mb-1 font-medium text-red-800 dark:text-red-100">
                    Registration Closed
                  </p>
                  <p className="text-sm text-red-600 dark:text-red-300">
                    Registration is no longer available for this event.
                  </p>
                </div>
              ))}

            {event.custom_details && (
              <Card className="bg-background">
                <CardHeader>
                  <CardTitle>Links & Resources</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 gap-3">
                    {event.custom_details.bracket_link && (
                      <Button variant="outline" asChild className="w-full">
                        <a
                          href={event.custom_details.bracket_link}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          View Bracket
                          <ExternalLink className="ml-2 h-4 w-4" />
                        </a>
                      </Button>
                    )}

                    {event.custom_details.stream_link && (
                      <Button variant="outline" asChild className="w-full">
                        <a
                          href={event.custom_details.stream_link}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <Twitch className="mr-2 h-4 w-4" />
                          Watch Stream
                        </a>
                      </Button>
                    )}

                    {event.custom_details.secondary_stream_link && (
                      <Button variant="outline" asChild className="w-full">
                        <a
                          href={event.custom_details.secondary_stream_link}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <Twitch className="mr-2 h-4 w-4" />
                          Secondary Stream
                        </a>
                      </Button>
                    )}

                    {event.custom_details.discord_link && (
                      <Button variant="outline" asChild className="w-full">
                        <a
                          href={event.custom_details.discord_link}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <MessageCircle className="mr-2 h-4 w-4" />
                          Join Discord
                        </a>
                      </Button>
                    )}

                    {event.custom_details.rules_document && (
                      <Button variant="outline" asChild className="w-full">
                        <a
                          href={event.custom_details.rules_document}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <FileText className="mr-2 h-4 w-4" />
                          View Rules
                        </a>
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}
            {/* Season Info */}
            {event.season && (
              <Card>
                <CardHeader>
                  <CardTitle>Season</CardTitle>
                </CardHeader>
                <CardContent>
                  <Badge variant="outline" className="text-sm">
                    {event.season.name}
                  </Badge>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function MainContentSwitcher(event: PublicEvent) {
  const getStatus = () => {
    if (!event) return null;
    const now = new Date();
    const start = new Date(event.start_date);
    const end = event.end_date ? new Date(event.end_date) : null;

    if (now < start) {
      return "upcoming";
    } else if (end && now > end) {
      return "completed";
    } else {
      return "ongoing";
    }
  };
  return (
    <Tabs defaultValue="matches" className="w-full">
      <TabsList>
        {getStatus() === "ongoing" && (
          <TabsTrigger
            value="stream"
            className="hover:text-foreground! cursor-pointer"
          >
            Stream
          </TabsTrigger>
        )}
        <TabsTrigger
          value="matches"
          className="hover:text-foreground! cursor-pointer"
        >
          Matches
        </TabsTrigger>
        <TabsTrigger
          value="bracket"
          className="hover:text-foreground! cursor-pointer"
        >
          Bracket
        </TabsTrigger>
        <TabsTrigger
          value="teams"
          className="hover:text-foreground! cursor-pointer"
        >
          Teams
        </TabsTrigger>
        <TabsTrigger
          value="info"
          className="hover:text-foreground! cursor-pointer"
        >
          Info
        </TabsTrigger>
      </TabsList>
      <TabsContent value="stream">
        <div>Stream Content Here</div>
      </TabsContent>
      <TabsContent value="bracket">{Bracket(event)}</TabsContent>
      <TabsContent value="matches">
        <div>Matches Content Here</div>
      </TabsContent>
      <TabsContent value="info">{Info(event)}</TabsContent>
    </Tabs>
  );
}

function Bracket(event: PublicEvent) {
  const bracketUrl = event.custom_details?.bracket_link;

  if (!bracketUrl) {
    return (
      <Card className="bg-background">
        <CardContent className="flex flex-col items-center justify-center py-12">
          <Trophy className="text-muted-foreground mb-4 h-12 w-12" />
          <p className="text-muted-foreground">
            No bracket available for this event
          </p>
        </CardContent>
      </Card>
    );
  }

  // Convert Challonge URL to embed format if needed
  const embedUrl = bracketUrl.includes("/module")
    ? bracketUrl
    : `${bracketUrl}/module?multiplier=1.4&transparent=1`;

  return (
    <div className="w-full overflow-clip rounded-lg">
      <iframe
        src={embedUrl}
        width="100%"
        height="400"
        sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
        referrerPolicy="no-referrer-when-downgrade"
        loading="lazy"
        title="Tournament Bracket"
        allowTransparency={true}
      ></iframe>
    </div>
  );
}

function Info(event: PublicEvent) {
  if (!event.custom_details) {
    return null;
  }
  return (
    <>
      <Card className="bg-background">
        <CardHeader>
          <CardTitle>About This Event</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground leading-relaxed">
            {event.description}
          </p>
        </CardContent>
      </Card>
    </>
  );
}
