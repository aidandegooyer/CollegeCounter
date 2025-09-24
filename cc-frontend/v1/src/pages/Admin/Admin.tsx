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
            Edit Team/Player
          </TabsTrigger>
          <TabsTrigger
            value="import"
            className="hover:text-foreground! cursor-pointer"
          >
            Import Matches
          </TabsTrigger>
          <TabsTrigger
            value="database"
            className="hover:text-foreground! cursor-pointer"
          >
            Database Viewer
          </TabsTrigger>
          <TabsTrigger
            value="delete-data"
            className="hover:text-foreground! cursor-pointer"
          >
            Delete Data
          </TabsTrigger>
          <TabsTrigger
            value="graphic"
            className="hover:text-foreground! cursor-pointer"
          >
            Graphic Generator
          </TabsTrigger>
          <TabsTrigger
            value="merge-teams"
            className="hover:text-foreground! cursor-pointer"
          >
            Merge Teams
          </TabsTrigger>
        </TabsList>
        <TabsContent value="control-panel">
          <ControlPanel />
        </TabsContent>
        <TabsContent value="edit">
          <EditTeamPlayer />
        </TabsContent>
        <TabsContent value="import">
          <ImportMatches />
        </TabsContent>
        <TabsContent value="database">
          <DatabaseViewer />
        </TabsContent>
        <TabsContent value="delete-data">
          <DeleteData />
        </TabsContent>
        <TabsContent value="graphic">
          <Graphic />
        </TabsContent>
        <TabsContent value="merge-teams">
          <MergeTeams />
        </TabsContent>
      </Tabs>
    </div>
  );
}
export default Admin;
