import { Button } from "@/components/ui/button";
import ImportMatches from "./ImportMatches";
import DatabaseViewer from "./DatabaseViewer";
import { getAuth, signOut } from "firebase/auth";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import DeleteData from "./DeleteData";
import ControlPanel from "./ControlPanel";
import EditTeamPlayer from "./EditTeamPlayer";
import Graphic from "./Graphic";
import MergeTeams from "./MergeTeams";
import EditMatch from "./EditMatch";
import EditEvent from "./EditEvent";

function Admin() {
  const auth = getAuth();
  const handleSignOut = async () => {
    try {
      await signOut(auth);
    } catch (error) {
      console.error("Error signing out:", error);
    }
  };
  return (
    <div className="mx-auto max-w-[1200px] p-4">
      <div className="flex justify-between">
        <h1 className="mb-4">Admin Panel</h1>
        <Button
          className="mb-4 cursor-pointer rounded bg-red-500 px-4 py-2 text-white hover:bg-red-600"
          onClick={() => {
            handleSignOut();
          }}
        >
          Sign Out
        </Button>
      </div>

      <Tabs defaultValue="control-panel" className="w-full">
        <TabsList>
          <TabsTrigger
            value="control-panel"
            className="hover:text-foreground! cursor-pointer"
          >
            Control Panel
          </TabsTrigger>
          <TabsTrigger
            value="edit"
            className="hover:text-foreground! cursor-pointer"
          >
            Edit/Create
          </TabsTrigger>

          <TabsTrigger
            value="import"
            className="hover:text-foreground! cursor-pointer"
          >
            Import Tools
          </TabsTrigger>
          <TabsTrigger
            value="database"
            className="hover:text-foreground! cursor-pointer"
          >
            Database Viewer
          </TabsTrigger>

          <TabsTrigger
            value="graphic"
            className="hover:text-foreground! cursor-pointer"
          >
            Graphic Generator
          </TabsTrigger>
        </TabsList>
        <TabsContent value="control-panel">
          <ControlPanel />
        </TabsContent>
        <TabsContent value="edit">{EditAndCreate()}</TabsContent>
        <TabsContent value="import">{ImportTools()}</TabsContent>
        <TabsContent value="database">
          <DatabaseViewer />
        </TabsContent>

        <TabsContent value="graphic">
          <Graphic />
        </TabsContent>
      </Tabs>
    </div>
  );
}
export default Admin;

function EditAndCreate() {
  return (
    <Tabs defaultValue="team-player">
      <TabsList>
        <TabsTrigger
          value="team-player"
          className="hover:text-foreground! cursor-pointer"
        >
          Team/Player
        </TabsTrigger>
        <TabsTrigger
          value="match"
          className="hover:text-foreground! cursor-pointer"
        >
          Match
        </TabsTrigger>
        <TabsTrigger
          value="event"
          className="hover:text-foreground! cursor-pointer"
        >
          Event
        </TabsTrigger>
      </TabsList>
      <TabsContent value="team-player">
        <EditTeamPlayer />
      </TabsContent>
      <TabsContent value="match">
        <EditMatch />
      </TabsContent>
      <TabsContent value="event">
        <EditEvent />
      </TabsContent>
    </Tabs>
  );
}

function ImportTools() {
  return (
    <Tabs defaultValue="import-matches">
      <TabsList>
        <TabsTrigger
          value="import-matches"
          className="hover:text-foreground! cursor-pointer"
        >
          Import Matches
        </TabsTrigger>
        <TabsTrigger
          value="merge-teams"
          className="hover:text-foreground! cursor-pointer"
        >
          Merge Teams
        </TabsTrigger>
        <TabsTrigger
          value="delete-data"
          className="hover:text-foreground! cursor-pointer"
        >
          Delete Data
        </TabsTrigger>
      </TabsList>
      <TabsContent value="import-matches">
        <ImportMatches />
      </TabsContent>
      <TabsContent value="merge-teams">
        <MergeTeams />
      </TabsContent>
      <TabsContent value="delete-data">
        <DeleteData />
      </TabsContent>
    </Tabs>
  );
}
