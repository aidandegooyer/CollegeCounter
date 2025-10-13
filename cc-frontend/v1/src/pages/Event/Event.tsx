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
  Hash,
} from "lucide-react";
import { usePublicEvent } from "@/services/hooks";

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
  const endDateTime = formatDateTime(event.end_date);
  const isUpcoming = startDateTime.full > new Date();
  const isOngoing =
    startDateTime.full <= new Date() && endDateTime.full >= new Date();
  const isPast = endDateTime.full < new Date();

  const getStatusBadge = () => {
    if (isOngoing) {
      return (
        <Badge variant="destructive" className="animate-pulse">
          Live Now
        </Badge>
      );
    }
    if (isUpcoming) {
      return <Badge variant="secondary">Upcoming</Badge>;
    }
    if (isPast) {
      return <Badge variant="outline">Completed</Badge>;
    }
  };

  return (
    <div className="app-container mx-4 flex justify-center">
      <div className="w-full max-w-[1200px] space-y-6">
        {/* Back Button */}
        <Button
          variant="ghost"
          onClick={() => navigate("/events")}
          className="mb-6"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Events
        </Button>

        {/* Hero Section */}
        <div className="relative">
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
            className={`${event.picture ? "absolute bottom-0 left-0 right-0 p-6 text-white" : "p-6"}`}
          >
            <div className="mb-2 flex flex-wrap items-start gap-3">
              <h1 className="text-3xl font-bold md:text-4xl">{event.name}</h1>
              {getStatusBadge()}
              {event.custom_details?.is_featured && (
                <Badge variant="default">Featured</Badge>
              )}
            </div>

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

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Main Content */}
          <div className="space-y-6 lg:col-span-2">
            {/* Event Description */}
            {event.description && (
              <Card>
                <CardHeader>
                  <CardTitle>About This Event</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground leading-relaxed">
                    {event.description}
                  </p>
                </CardContent>
              </Card>
            )}

            {/* Competition Details */}
            {event.custom_details && (
              <Card>
                <CardHeader>
                  <CardTitle>Competition Details</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
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

                  {event.custom_details.game_mode && (
                    <div className="pt-2">
                      <Badge variant="outline" className="text-sm">
                        {event.custom_details.game_mode}
                      </Badge>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Links & Resources */}
            {event.custom_details && (
              <Card>
                <CardHeader>
                  <CardTitle>Links & Resources</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    {event.custom_details.registration_link &&
                      event.custom_details.registration_open && (
                        <Button asChild className="w-full">
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
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Event Schedule */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CalendarDays className="h-5 w-5" />
                  Schedule
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="mb-1 font-medium text-green-600">Event Start</p>
                  <p className="text-sm">{startDateTime.date}</p>
                  <p className="text-muted-foreground text-sm">
                    {startDateTime.time}
                  </p>
                </div>

                {startDateTime.date !== endDateTime.date && (
                  <div>
                    <p className="mb-1 font-medium text-red-600">Event End</p>
                    <p className="text-sm">{endDateTime.date}</p>
                    <p className="text-muted-foreground text-sm">
                      {endDateTime.time}
                    </p>
                  </div>
                )}

                {event.custom_details?.registration_deadline && (
                  <div>
                    <p className="mb-1 font-medium text-orange-600">
                      Registration Deadline
                    </p>
                    <p className="text-sm">
                      {formatDate(
                        new Date(event.custom_details.registration_deadline),
                      )}
                    </p>
                    <p className="text-muted-foreground text-sm">
                      {formatTime(
                        new Date(event.custom_details.registration_deadline),
                      )}
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Registration Status */}
            {event.custom_details && (
              <Card>
                <CardHeader>
                  <CardTitle>Registration</CardTitle>
                </CardHeader>
                <CardContent>
                  {event.custom_details.registration_open ? (
                    <div className="rounded-lg bg-green-50 p-3 dark:bg-green-950/20">
                      <p className="mb-1 font-medium text-green-800 dark:text-green-100">
                        Registration Open
                      </p>
                      <p className="text-sm text-green-600 dark:text-green-300">
                        Sign up now to secure your spot!
                      </p>
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
                  )}
                </CardContent>
              </Card>
            )}

            {/* Social */}
            {event.custom_details?.twitter_hashtag && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Hash className="h-5 w-5" />
                    Social
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <Button variant="outline" asChild className="w-full">
                    <a
                      href={`https://twitter.com/hashtag/${event.custom_details.twitter_hashtag.replace("#", "")}`}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {event.custom_details.twitter_hashtag}
                      <ExternalLink className="ml-2 h-4 w-4" />
                    </a>
                  </Button>
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
