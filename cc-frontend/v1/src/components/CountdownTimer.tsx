import { useState, useEffect } from "react";

interface TimeRemaining {
  days: number;
  hours: number;
  minutes: number;
  seconds: number;
}

export function CountdownTimer({ targetDate }: { targetDate: Date }) {
  const [timeRemaining, setTimeRemaining] = useState<TimeRemaining>({
    days: 0,
    hours: 0,
    minutes: 0,
    seconds: 0,
  });
  const [isExpired, setIsExpired] = useState(false);

  useEffect(() => {
    const calculateTimeRemaining = () => {
      const now = new Date().getTime();
      const target = targetDate.getTime();
      const difference = target - now;

      if (difference <= 0) {
        setIsExpired(true);
        setTimeRemaining({ days: 0, hours: 0, minutes: 0, seconds: 0 });
        return;
      }

      const days = Math.floor(difference / (1000 * 60 * 60 * 24));
      const hours = Math.floor(
        (difference % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60),
      );
      const minutes = Math.floor((difference % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((difference % (1000 * 60)) / 1000);

      setTimeRemaining({ days, hours, minutes, seconds });
      setIsExpired(false);
    };

    // Calculate immediately
    calculateTimeRemaining();

    // Update every second
    const interval = setInterval(calculateTimeRemaining, 1000);

    // Cleanup interval on unmount
    return () => clearInterval(interval);
  }, [targetDate]);

  if (isExpired) {
    return <div className=""></div>;
  }

  return (
    <div className="flex flex-wrap justify-center gap-4 text-center">
      {timeRemaining.days > 0 && (
        <div className="flex flex-col">
          <span className="text-3xl font-bold">
            {timeRemaining.days.toString().padStart(2, "0")}
          </span>
          <span className="text-sm uppercase tracking-wide text-gray-600">
            {timeRemaining.days === 1 ? "Day" : "Days"}
          </span>
        </div>
      )}

      <div className="flex flex-col">
        <span className="text-3xl font-bold">
          {timeRemaining.hours.toString().padStart(2, "0")}
        </span>
        <span className="text-sm uppercase tracking-wide text-gray-600">
          Hr
        </span>
      </div>

      <div className="flex flex-col">
        <span className="text-3xl font-bold">
          {timeRemaining.minutes.toString().padStart(2, "0")}
        </span>
        <span className="text-sm uppercase tracking-wide text-gray-600">
          Min
        </span>
      </div>

      <div className="flex flex-col">
        <span className="text-3xl font-bold">
          {timeRemaining.seconds.toString().padStart(2, "0")}
        </span>
        <span className="text-sm uppercase tracking-wide text-gray-600">
          Sec
        </span>
      </div>
    </div>
  );
}
