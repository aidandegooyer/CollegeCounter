import { Button } from "@/components/ui/button";
import ImportMatches from "./ImportMatches";
import DatabaseViewer from "./DatabaseViewer";
import { getAuth, signOut } from "firebase/auth";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import ClearDatabase from "./ClearDatabase";

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

      <Tabs defaultValue="import" className="w-full">
        <TabsList>
          <TabsTrigger value="import">Import Matches</TabsTrigger>
          <TabsTrigger value="database">Database Viewer</TabsTrigger>
          <TabsTrigger value="clear-database">Clear Database</TabsTrigger>
        </TabsList>
        <TabsContent value="import">
          <ImportMatches />
        </TabsContent>
        <TabsContent value="database">
          <DatabaseViewer />
        </TabsContent>
        <TabsContent value="clear-database">
          <ClearDatabase />
        </TabsContent>
      </Tabs>
    </div>
  );
}
export default Admin;
