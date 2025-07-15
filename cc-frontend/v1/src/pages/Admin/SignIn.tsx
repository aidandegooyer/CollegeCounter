import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getAuth, signInWithEmailAndPassword } from "firebase/auth";

function SignIn() {
  const auth = getAuth();

  async function handleSignIn(email: string, password: string) {
    try {
      await signInWithEmailAndPassword(auth, email, password);
    } catch (error: any) {
      alert(error.message);
    } finally {
      window.location.href = "/admin";
    }
  }
  return (
    <div className="app-container mx-4 flex justify-center">
      <div className="max-width-[600px] space-y-4">
        <h1>Sign In</h1>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            const email = (
              e.currentTarget.elements.namedItem("email") as HTMLInputElement
            ).value;
            const password = (
              e.currentTarget.elements.namedItem("password") as HTMLInputElement
            ).value;
            handleSignIn(email, password);
          }}
          className="space-y-4"
        >
          <div>
            <Label htmlFor="email">Email:</Label>
            <Input type="email" id="email" name="email" required />
          </div>
          <div>
            <Label htmlFor="password">Password:</Label>
            <Input type="password" id="password" name="password" required />
          </div>
          <Button type="submit" className="cursor-pointer">
            Sign In
          </Button>
        </form>
      </div>
    </div>
  );
}

export default SignIn;
