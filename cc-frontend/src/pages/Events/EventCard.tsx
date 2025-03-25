import React from "react";
import Card from "react-bootstrap/Card";
import Button from "react-bootstrap/Button";
import { Event } from "../../types";
import { Link } from "react-router-dom";

type EventCardProps = {
  event: Event;
};

const EventCard: React.FC<EventCardProps> = ({ event }) => {
  return (
    <Card>
      <Card.Body>
        <h1>{event.title}</h1>
        <h3>{event.description}</h3>
        <h5 style={{ color: "grey" }}>
          {new Date(event.start_date * 1000).toLocaleDateString()} -{" "}
          {new Date(event.end_date * 1000).toLocaleDateString()}
        </h5>
        <Link to={`/events/${event.event_id}`}>
          <Button>View Event</Button>
        </Link>
      </Card.Body>
    </Card>
  );
};

export default EventCard;
