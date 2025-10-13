import { Spinner } from "@/components/ui/shadcn-io/spinner";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  CalendarDays,
  MapPin,
  Trophy,
  Users,
  ExternalLink,
  Twitch,
  MessageCircle,
} from "lucide-react";

// Simple Badge component
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
import { usePublicEvents } from "@/services/hooks";
import type { PublicEvent } from "@/services/api";

export function Events() {
  const {
    data: eventsResponse,
    isLoading: eventsLoading,
    error,
  } = usePublicEvents({
    sort: "start_date",
    order: "asc",
    page_size: 20,
  });

  const events = eventsResponse?.results || [];

  if (error) {
    return (
      <div className="app-container mx-4 flex justify-center">
        <div className="matches w-full max-w-[1000px]">
          <h1 className="mb-4 text-3xl font-bold">Events</h1>
          <div className="flex h-40 items-center justify-center">
            <p className="text-red-600">
              Error loading events: {error.message}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container mx-4 flex justify-center">
      <div className="matches w-full max-w-[1200px]">
        <div className="mb-6">
          <h1 className="mb-2 text-3xl font-bold">Events</h1>
          <p className="text-muted-foreground">
            Discover upcoming tournaments, competitions, and community events
          </p>
        </div>

        {eventsLoading ? (
          <div className="flex h-40 items-center justify-center">
            <Spinner className="h-8 w-8" />
          </div>
        ) : events.length === 0 ? (
          <div className="flex h-40 flex-col items-center justify-center text-center">
            <Trophy className="text-muted-foreground mb-3 h-12 w-12" />
            <h3 className="mb-2 text-lg font-semibold">No Events Found</h3>
            <p className="text-muted-foreground">
              There are currently no upcoming events. Check back later!
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6">
            {events.map((event) => (
              <Event key={event.id} event={event} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

interface EventProps {
  event: PublicEvent;
}

function Event({ event }: EventProps) {
  const startDate = new Date(event.start_date);
  const endDate = new Date(event.end_date);
  const isUpcoming = startDate > new Date();
  const isOngoing = startDate <= new Date() && endDate >= new Date();
  const isPast = endDate < new Date();

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

  const getStatusBadge = () => {
    if (isOngoing) {
      return (
        <Badge variant="destructive" className="animate-pulse">
          Live
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
    <Card className="overflow-hidden transition-shadow hover:shadow-lg">
      <div className="flex flex-col md:flex-row">
        {/* Event Image */}
        {event.picture && (
          <div className="h-48 md:h-auto md:w-64">
            <img
              src={event.picture}
              alt={event.name}
              className="h-full w-full object-cover"
            />
          </div>
        )}

        {/* Event Content */}
        <div className="flex-1">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <CardTitle className="text-xl">{event.name}</CardTitle>
                  {getStatusBadge()}
                  {event.custom_details?.is_featured && (
                    <Badge variant="default">Featured</Badge>
                  )}
                </div>

                <div className="text-muted-foreground flex flex-wrap items-center gap-4 text-sm">
                  <div className="flex items-center gap-1">
                    <CalendarDays className="h-4 w-4" />
                    <span>{formatDate(startDate)}</span>
                  </div>
                  {startDate.toDateString() !== endDate.toDateString() && (
                    <span>→ {formatDate(endDate)}</span>
                  )}
                </div>

                <div className="text-muted-foreground flex items-center gap-1 text-sm">
                  <span>{formatTime(startDate)}</span>
                  {startDate.getTime() !== endDate.getTime() && (
                    <span>- {formatTime(endDate)}</span>
                  )}
                </div>
              </div>

              {event.winner && (
                <div className="flex items-center gap-2 text-sm">
                  <Trophy className="h-4 w-4 text-yellow-500" />
                  <span className="font-medium">{event.winner.name}</span>
                </div>
              )}
            </div>

            {event.description && (
              <CardDescription className="text-base">
                {event.description}
              </CardDescription>
            )}
          </CardHeader>

          <CardContent>
            {/* Event Details */}
            {event.custom_details && (
              <div className="mb-4 space-y-3">
                {/* Prize Pool */}
                {event.custom_details.prize_pool && (
                  <div className="flex items-center gap-2 text-sm">
                    <Trophy className="h-4 w-4 text-yellow-500" />
                    <span className="font-medium">Prize Pool:</span>
                    <span>
                      {event.custom_details.prize_currency}{" "}
                      {event.custom_details.prize_pool}
                    </span>
                  </div>
                )}

                {/* Max Teams */}
                {event.custom_details.max_teams && (
                  <div className="flex items-center gap-2 text-sm">
                    <Users className="h-4 w-4" />
                    <span className="font-medium">Max Teams:</span>
                    <span>{event.custom_details.max_teams}</span>
                  </div>
                )}

                {/* Format & Game Mode */}
                <div className="flex flex-wrap gap-4 text-sm">
                  {event.custom_details.format && (
                    <div className="flex items-center gap-1">
                      <MapPin className="h-4 w-4" />
                      <span>{event.custom_details.format}</span>
                    </div>
                  )}
                  {event.custom_details.game_mode && (
                    <Badge variant="outline">
                      {event.custom_details.game_mode}
                    </Badge>
                  )}
                </div>

                {/* Registration */}
                {event.custom_details.registration_open &&
                  event.custom_details.registration_deadline && (
                    <div className="rounded-lg bg-blue-50 p-3 dark:bg-blue-950/20">
                      <p className="text-sm font-medium text-blue-900 dark:text-blue-100">
                        Registration Open
                      </p>
                      <p className="text-xs text-blue-700 dark:text-blue-300">
                        Deadline:{" "}
                        {new Date(
                          event.custom_details.registration_deadline,
                        ).toLocaleDateString()}
                      </p>
                    </div>
                  )}
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex flex-wrap gap-2">
              {event.custom_details?.registration_link &&
                event.custom_details.registration_open && (
                  <Button asChild>
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

              {event.custom_details?.bracket_link && (
                <Button variant="outline" asChild>
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

              {event.custom_details?.stream_link && (
                <Button variant="outline" asChild>
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

              {event.custom_details?.discord_link && (
                <Button variant="outline" asChild>
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
            </div>
          </CardContent>
        </div>
      </div>
    </Card>
  );
}
