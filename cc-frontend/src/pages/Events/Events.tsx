import { useQuery } from "@tanstack/react-query";
import { Container, Spinner } from "react-bootstrap";
import { Event } from "../../types";
import EventCard from "./EventCard";
import { useEffect } from "react";
const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL || "https://api.collegecounter.org";

const fetchEvents = async () => {
  const response = await fetch(`${apiBaseUrl}/events`);
  return response.json();
};

const Events = () => {
  const {
    data: events,
    isLoading: eventLoading,
    error: eventErrorObj,
    isError: eventError,
  } = useQuery<Event[]>({
    queryKey: ["events"],
    queryFn: () => fetchEvents(),
    staleTime: 1000 * 60 * 10,
  });

  useEffect(() => {
    document.title = "CC - Events";
  }, []);

  const now = new Date();

  const ongoingEvents = events?.filter(
    (event) =>
      new Date(event.start_date * 1000) <= now &&
      new Date(event.end_date * 1000) >= now
  );
  const upcomingEvents = events?.filter(
    (event) => new Date(event.start_date * 1000) > now
  );
  const pastEvents = events?.filter(
    (event) => new Date(event.end_date * 1000) < now
  );

  if (eventLoading) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100vh",
        }}
      >
        <Spinner animation="border" />
      </div>
    );
  }

  if (eventError) {
    return (
      <Container>
        <h1>Error</h1>
        <p>{eventErrorObj?.message}</p>
      </Container>
    );
  }

  return (
    <Container
      style={{ marginTop: "0.5rem", maxWidth: "1300px", padding: "0 1rem" }}
    >
      <Container style={{ maxWidth: "800px" }}>
        <h1 className="text-center">Events</h1>
        <h3 style={{ marginTop: "2rem" }}>Ongoing Events</h3>
        {ongoingEvents?.map((event) => (
          <EventCard key={event.event_id} event={event} />
        ))}
        <h3 style={{ marginTop: "2rem" }}>Upcoming Events</h3>
        {upcomingEvents?.map((event) => (
          <EventCard key={event.event_id} event={event} />
        ))}
        <h3 style={{ marginTop: "2rem" }}>Past Events</h3>
        {pastEvents?.map((event) => (
          <EventCard key={event.event_id} event={event} />
        ))}
      </Container>
    </Container>
  );
};

export default Events;
