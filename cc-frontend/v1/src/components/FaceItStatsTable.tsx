import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import Logo from "@/components/Logo";
import type { FaceItPlayerStats } from "@/services/faceit-stats";

interface FaceItStatsTableProps {
  teamName?: string;
  teamLogo?: string;
  players: FaceItPlayerStats[];
}

export function FaceItStatsTable({
  teamName,
  teamLogo,
  players,
}: 

FaceItStatsTableProps) {
  return (
    <div>
      {teamName && (
        <div className="mb-2 flex items-center gap-2">
          <Logo
            src={teamLogo}
            type="team"
            alt={`${teamName} logo`}
            className="h-8 w-8 object-contain"
          />
          <h3 className="text-lg font-semibold">{teamName}</h3>
        </div>
      )}
      <Table>
        <TableHeader>
          <TableRow className="bg-muted">
            <TableHead>Player</TableHead>
            <TableHead className="text-right">K</TableHead>
            <TableHead className="text-right">D</TableHead>
            <TableHead className="text-right">A</TableHead>
            <TableHead className="text-right">+/-</TableHead>
            <TableHead className="text-right">K/D</TableHead>
            <TableHead className="text-right">HS%</TableHead>
            <TableHead className="text-right">ADR</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {[...players]
            .sort((a, b) => (b.stat_kills ?? -1) - (a.stat_kills ?? -1))
            .map((player) => {
              const plusMinus =
                player.stat_kills !== undefined &&
                player.stat_deaths !== undefined
                  ? player.stat_kills - player.stat_deaths
                  : undefined;

              return (
                <TableRow key={player.player_id}>
                  <TableCell className="w-24 font-medium">
                    {player.stat_username || "Unknown"}
                  </TableCell>
                  <TableCell className="text-right">
                    {player.stat_kills ?? "N/A"}
                  </TableCell>
                  <TableCell className="text-right">
                    {player.stat_deaths ?? "N/A"}
                  </TableCell>
                  <TableCell className="text-right">
                    {player.stat_assists ?? "N/A"}
                  </TableCell>

                  <TableCell
                    className={`text-right ${plusMinus !== undefined && plusMinus > 0 ? "text-green-500" : plusMinus !== undefined && plusMinus < 0 ? "text-red-500" : "text-muted-foreground"}`}
                  >
                    {plusMinus === undefined ? "N/A" : plusMinus > 0 ? `+${plusMinus}` : plusMinus}
                  </TableCell>

                  <TableCell className="text-right">{player.stat_kd}</TableCell>

                  <TableCell className="text-right">
                    {player.stat_hsp || "N/A"}
                  </TableCell>

                  <TableCell
                    className={`text-right ${
                      player.stat_adr && parseInt(player.stat_adr) >= 90
                        ? "text-green-300"
                        : player.stat_adr && parseInt(player.stat_adr) < 60
                          ? "text-red-300"
                          : player.stat_adr &&
                              parseInt(player.stat_adr) >= 60 &&
                              parseInt(player.stat_adr) < 90
                            ? "text-white"
                            : "text-muted-foreground"
                    }`}
                  >
                    {player.stat_adr || "N/A"}
                  </TableCell>
                </TableRow>
              );
            })}
        </TableBody>
      </Table>
    </div>
  );
}
