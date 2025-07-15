import { useState } from "react";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";

function SelectPlatform() {
  return (
    <div className="mb-8 flex flex-col items-center justify-center space-y-4">
      <h1 className="text-3xl">Select Platform</h1>
      <RadioGroup defaultValue="option-one">
        <div className="flex items-center space-x-2">
          <RadioGroupItem value="option-one" id="option-one" />
          <Label htmlFor="option-one">Faceit</Label>
        </div>
        <div className="flex items-center space-x-2">
          <RadioGroupItem value="option-two" id="option-two" />
          <Label htmlFor="option-two">Playfly</Label>
        </div>
      </RadioGroup>
    </div>
  );
}
function SelectLeagueOrEvent() {
  return (
    <div className="mb-8 flex flex-col items-center justify-center space-y-4">
      <h1 className="text-3xl">Select Type</h1>
      <RadioGroup defaultValue="option-one">
        <div className="flex items-center space-x-2">
          <RadioGroupItem value="option-one" id="option-one" />
          <Label htmlFor="option-one">Event (Bracket based)</Label>
        </div>
        <div className="flex items-center space-x-2">
          <RadioGroupItem value="option-two" id="option-two" />
          <Label htmlFor="option-two">League</Label>
        </div>
      </RadioGroup>
    </div>
  );
}
function SelectOrCreateSeason() {
  return (
    <div className="mb-8 flex flex-col items-center justify-center space-y-4">
      <h1 className="text-3xl">Select Season</h1>
      <Select>
        <SelectTrigger className="w-[180px]">
          <SelectValue placeholder="Season" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="light">TestSeason1</SelectItem>
          <SelectItem value="dark">TestSeason2</SelectItem>
          <SelectItem value="system">TestSeason3</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
}
function MetadataForm() {
  return (
    <div className="mb-8 flex flex-col items-center justify-center space-y-4">
      <h1 className="text-3xl">Input Data</h1>
      <Select>
        <SelectTrigger className="w-[180px]">
          <SelectValue placeholder="Competition" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="necc">NECC</SelectItem>
          <SelectItem value="playfly">PlayFly</SelectItem>
        </SelectContent>
      </Select>
      <Label>Name</Label>
      <Input className="max-w-xl" placeholder="Name" />
    </div>
  );
}
function ImportPreview() {
  return <div>Import Preview Component</div>;
}
function ParticipantMatcher() {
  return <div>Participant Matcher Component</div>;
}

function ImportFlow(step: number) {
  switch (step) {
    case 0:
      return (
        <>
          <SelectPlatform />{" "}
        </>
      );
    case 1:
      return (
        <>
          <SelectLeagueOrEvent />
        </>
      );
    case 2:
      return (
        <>
          <SelectOrCreateSeason />
        </>
      );
    case 3:
      return (
        <>
          <MetadataForm />
        </>
      );
    case 4:
      return (
        <>
          <ImportPreview />
        </>
      );
    case 5:
      return (
        <>
          <ParticipantMatcher />
        </>
      );
  }
}

function ImportMatches() {
  const [step, setStep] = useState(0);
  const nextStep = () => setStep((prev) => Math.min(prev + 1, 5));

  return (
    <>
      <div className="flex justify-center">
        <div className="max-w-[600px]">
          <h1 className="mb-8">Import Matches</h1>

          {ImportFlow(step)}
          <div className="flex justify-end">
            <button
              className="bg-primary cursor-pointer rounded-md p-2 px-4 text-end transition-all duration-300 hover:bg-[#b5670b]"
              onClick={nextStep}
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

export default ImportMatches;
