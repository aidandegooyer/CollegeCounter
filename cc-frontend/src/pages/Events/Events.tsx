import { useQuery } from "@tanstack/react-query";
import { Container } from "react-bootstrap";
import { Event } from "../../types";
import { Link } from "react-router";
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
  return (
    <Container
      style={{ marginTop: "0.5rem", maxWidth: "1300px", padding: "0 1rem" }}
    >
      <Container style={{ maxWidth: "800px" }}>
        <h1 className="text-center">Events</h1>
        <h3>Ongoing Events</h3>
        {events?.map((event) => (
          <div key={event.event_id}>
            <Link to={`/events/${event.event_id}`}>{event.title}</Link>
          </div>
        ))}
        <h3>Upcoming Events</h3>

        <h3>Past Events</h3>
      </Container>
    </Container>
  );
};

export default Events;
