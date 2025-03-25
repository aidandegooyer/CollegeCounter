import React from "react";
import ResponsiveBracket from "./Bracket/ResponsiveBracket";
import { Container, Spinner } from "react-bootstrap";
import "./EventPage.css";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Event, EventMatch } from "../../types";
const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL || "https://api.collegecounter.org";

const fetchEvents = async (event_id: string) => {
  const response = await fetch(`${apiBaseUrl}/event/${event_id}`);
  return response.json();
};

const fetchEventMatches = async (event_id: string) => {
  const response = await fetch(`${apiBaseUrl}/event/${event_id}/matches`);
  return response.json();
};

const EventPage: React.FC = () => {
  const { event_id } = useParams<{ event_id: string }>();
  const {
    data: event_obj,
    isLoading: eventLoading,
    error: eventErrorObj,
    isError: eventError,
  } = useQuery<Event>({
    queryKey: ["event", event_id],
    queryFn: () => fetchEvents(event_id!),
    staleTime: 1000 * 60 * 10,
    enabled: !!event_id,
  });

  const {
    data: eventMatches,
    isLoading: eventMatchesLoading,
    error: eventMatchesErrorObj,
    isError: eventMatchesError,
  } = useQuery<EventMatch[]>({
    queryKey: ["event", event_id, "matches"],
    queryFn: () => fetchEventMatches(event_id!),
    staleTime: 1000 * 60 * 10,
    enabled: !!event_id,
  });
  if (eventLoading || eventMatchesLoading) {
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
  if (eventError || eventMatchesError) {
    return (
      <Container
        style={{ marginTop: "0.5rem", padding: "0 1rem" }}
        className="text-center"
      >
        <h1>
          Error: {eventErrorObj?.message} {eventMatchesErrorObj?.message}
        </h1>
      </Container>
    );
  }

  return (
    <Container style={{ marginTop: "0.5rem", padding: "0 1rem" }}>
      <h1 className="text-center">{event_obj?.title}</h1>
      <h3 className="text-center">{event_obj?.description}</h3>
      <h5 className="text-center" style={{ color: "grey" }}>
        {new Date(event_obj?.start_date! * 1000).toLocaleDateString()} -{" "}
        {new Date(event_obj?.end_date! * 1000).toLocaleDateString()}
      </h5>
      {eventMatches && (
        <div
          style={{
            overflowX: "auto",
            overflowY: "hidden",
            width: "100%",
          }}
        >
          <div style={{ display: "inline-block" }}>
            <ResponsiveBracket matches={eventMatches} />
          </div>
        </div>
      )}
    </Container>
  );
};

export default EventPage;
