import { useQuery } from "@tanstack/react-query";
import { Container, Spinner } from "react-bootstrap";
import { Event } from "../../types";
import EventCard from "./EventCard";
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
        {events?.map((event) => (
          <EventCard key={event.event_id} event={event} />
        ))}
        <h3 style={{ marginTop: "2rem" }}>Upcoming Events</h3>

        <h3 style={{ marginTop: "2rem" }}>Past Events</h3>
      </Container>
    </Container>
  );
};

export default Events;
