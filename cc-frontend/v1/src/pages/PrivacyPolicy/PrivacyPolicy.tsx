import type { ReactNode } from "react";

const LAST_UPDATED = "October 7, 2026";
const CONTACT_EMAIL = "collegiatecounter@gmail.com";

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-3">
      <h2 className="text-2xl font-semibold">{title}</h2>
      <div className="text-muted-foreground space-y-3 leading-relaxed">
        {children}
      </div>
    </section>
  );
}

function ExternalLink({
  href,
  children,
}: {
  href: string;
  children: ReactNode;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-foreground underline"
    >
      {children}
    </a>
  );
}

export default function PrivacyPolicy() {
  document.title = "Privacy Policy - College Counter";

  return (
    <main className="app-container mx-auto w-full max-w-[900px] px-4 py-8">
      <div className="space-y-8 rounded-2xl border-2 p-6 shadow-sm md:p-10">
        <header className="space-y-2">
          <h1 className="text-4xl font-bold">Privacy Policy</h1>
          <p className="text-muted-foreground text-sm">
            Last updated: {LAST_UPDATED}
          </p>
        </header>

        <p className="text-muted-foreground leading-relaxed">
          College Counter (collegecounter.org) is operated by Station XI LLC
          ("we", "us"). This policy explains what information we collect when
          you use the site, how we use it, and the choices you have. You don't
          need an account to use College Counter.
        </p>

        <Section title="Information we collect">
          <p>
            <span className="text-foreground font-semibold">Analytics.</span> We
            use Google Analytics to understand how the site is used, such as
            which pages are visited and roughly where visitors are located.
            Google Analytics uses cookies and collects information like your IP
            address, browser and device type, and the pages you view.
          </p>
          <p>
            <span className="text-foreground font-semibold">Server logs.</span>{" "}
            Like most websites, our servers automatically record basic request
            information, including IP address, browser user agent, the page
            requested, and the time of the request. We use these logs to keep
            the site running, debug problems, and prevent abuse.
          </p>
          <p>
            <span className="text-foreground font-semibold">
              Administrator accounts.
            </span>{" "}
            Sign-in is only used by College Counter staff. For those accounts we
            store an email address through Firebase Authentication, and the
            browser keeps a sign-in session.
          </p>
        </Section>

        <Section title="Player and team information">
          <p>
            College Counter publishes rankings, rosters, and match results for
            collegiate Counter-Strike. To do that we collect information that
            players and teams have already made public on competition platforms
            such as FACEIT and league websites, including player names or
            nicknames, profile pictures, Steam and FACEIT identifiers, FACEIT
            skill level and Elo, team rosters, and match results.
          </p>
          <p>
            If you are a player and want information about you corrected,
            hidden, or removed, email us at{" "}
            <a
              href={`mailto:${CONTACT_EMAIL}`}
              className="text-foreground underline"
            >
              {CONTACT_EMAIL}
            </a>
            .
          </p>
        </Section>

        <Section title="Third-party services">
          <p>
            Some parts of the site are provided by other companies, which may
            receive your IP address and set their own cookies under their own
            privacy policies:
          </p>
          <ul className="list-disc space-y-2 pl-6">
            <li>
              <span className="text-foreground">Google Analytics</span> (usage
              analytics) and{" "}
              <span className="text-foreground">Google Fonts</span> (fonts) —{" "}
              <ExternalLink href="https://policies.google.com/privacy">
                Google Privacy Policy
              </ExternalLink>
            </li>
            <li>
              <span className="text-foreground">Twitch</span> (embedded live
              streams on event pages) —{" "}
              <ExternalLink href="https://www.twitch.tv/p/legal/privacy-notice/">
                Twitch Privacy Notice
              </ExternalLink>
            </li>
            <li>
              <span className="text-foreground">Sanity</span> (news articles) —{" "}
              <ExternalLink href="https://www.sanity.io/legal/privacy">
                Sanity Privacy Policy
              </ExternalLink>
            </li>
            <li>
              <span className="text-foreground">Firebase</span> (staff sign-in
              and image hosting) —{" "}
              <ExternalLink href="https://firebase.google.com/support/privacy">
                Firebase Privacy and Security
              </ExternalLink>
            </li>
          </ul>
        </Section>

        <Section title="How we use information">
          <p>
            We use the information above to run and improve College Counter,
            publish rankings and match results, understand which features are
            used, and keep the site secure. We do not sell your personal
            information, and we do not use it for advertising.
          </p>
        </Section>

        <Section title="Your choices">
          <ul className="list-disc space-y-2 pl-6">
            <li>
              You can block or delete cookies in your browser settings. The site
              works without analytics cookies.
            </li>
            <li>
              You can opt out of Google Analytics with Google's{" "}
              <ExternalLink href="https://tools.google.com/dlpage/gaoptout">
                opt-out browser add-on
              </ExternalLink>
              .
            </li>
            <li>
              Depending on where you live, you may have the right to request
              access to, correction of, or deletion of your personal
              information. Email us at{" "}
              <a
                href={`mailto:${CONTACT_EMAIL}`}
                className="text-foreground underline"
              >
                {CONTACT_EMAIL}
              </a>{" "}
              and we'll respond as required by applicable law.
            </li>
          </ul>
        </Section>

        <Section title="Children">
          <p>
            College Counter is intended for a general and collegiate audience
            and is not directed to children under 13. We don't knowingly collect
            personal information from children under 13.
          </p>
        </Section>

        <Section title="Changes to this policy">
          <p>
            We may update this policy from time to time. When we do, we'll
            change the "Last updated" date at the top of this page.
          </p>
        </Section>

        <Section title="Contact">
          <p>
            Questions about this policy can be sent to{" "}
            <a
              href={`mailto:${CONTACT_EMAIL}`}
              className="text-foreground underline"
            >
              {CONTACT_EMAIL}
            </a>
            .
          </p>
        </Section>
      </div>
    </main>
  );
}
