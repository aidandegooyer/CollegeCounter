import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface PlayerStats {
  stat_username?: string;
  stat_kills: number;
  stat_deaths: number;
  stat_assists: number;
  stat_adr?: string;
  stat_khs?: string;
  stat_1stk: number;
  stat_clutch: number;
  stat_mvps: number;
  stat_score: number;
}

interface PlayerStatsTableProps {
  teamName?: string;
  players: PlayerStats[];
}

export function PlayerStatsTable({ teamName, players }: PlayerStatsTableProps) {
  return (
    <div>
      {teamName && <h3 className="mb-2 text-lg font-semibold">{teamName}</h3>}
      <Table>
        <TableHeader>
          <TableRow className="bg-muted">
            <TableHead>Player</TableHead>
            <TableHead className="text-right">K</TableHead>
            <TableHead className="text-right">D</TableHead>
            <TableHead className="text-right">A</TableHead>
            <TableHead className="text-right">+/-</TableHead>
            <TableHead className="text-right">ADR</TableHead>

            <TableHead className="text-right">Clutch Wins</TableHead>
            <TableHead className="text-right">MVPs</TableHead>
            <TableHead className="text-right">Score</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {players
            ?.sort((a, b) => b.stat_score - a.stat_score)
            .map((player, idx) => {
              const plusMinus = player.stat_kills - player.stat_deaths;
              return (
                <TableRow key={idx}>
                  <TableCell className="font-medium">
                    {player.stat_username || "Unknown"}
                  </TableCell>
                  <TableCell className="text-right">
                    {player.stat_kills}
                  </TableCell>
                  <TableCell className="text-right">
                    {player.stat_deaths}
                  </TableCell>
                  <TableCell className="text-right">
                    {player.stat_assists}
                  </TableCell>
                  <TableCell className="text-right">
                    {plusMinus > 0 ? `+${plusMinus}` : plusMinus}
                  </TableCell>
                  <TableCell className="text-right">
                    {player.stat_adr || "N/A"}
                  </TableCell>

                  <TableCell className="text-right">
                    {player.stat_clutch}
                  </TableCell>
                  <TableCell className="text-right">
                    {player.stat_mvps}
                  </TableCell>
                  <TableCell className="text-right">
                    {player.stat_score}
                  </TableCell>
                </TableRow>
              );
            })}
        </TableBody>
      </Table>
    </div>
  );
}
