/**
 * The contact form on worldbytouch.com.
 *
 * A plain HTML form posts here and the answer is a redirect, so the whole thing
 * works with JavaScript switched off and the page stays free of third-party
 * requests, which is what the footer claims.
 *
 * Environment (Pages project settings, not this file):
 *   RESEND_API_KEY  secret, from the Resend dashboard
 *   RESEND_FROM     verified sender on the domain
 *   CONTACT_TO      inbox that receives the enquiries
 */

const ENDPOINT = "https://api.resend.com/emails";
const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/;

const TOPICS = {
  commission: "Commission",
  support: "Support",
  other: "Something else",
};

const COPY = {
  en: {
    lang: "en",
    title: "Message not sent – World by Touch",
    heading: "That did not go through",
    body: "Nothing was sent, and nothing was lost on your side either: copy your message and " +
          "email it to me directly and I will answer the same way.",
    back: "Back to the site",
    home: "/",
  },
  sr: {
    lang: "sr",
    title: "Poruka nije poslata – World by Touch",
    heading: "Ovo nije prošlo",
    body: "Ništa nije poslato, ali ništa nije ni izgubljeno: kopirajte svoju poruku i " +
          "pošaljite mi je direktno mejlom, odgovoriću na isti način.",
    back: "Nazad na sajt",
    home: "/sr/",
  },
};

function problem(url, lang, status) {
  const t = COPY[lang] || COPY.en;
  const to = "glebmaksimov@worldbytouch.com";
  const html = `<!doctype html>
<html lang="${t.lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>${t.title}</title>
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/style.css">
</head>
<body>
<main id="main">
  <section>
    <div class="wrap">
      <div class="prose">
        <h1>${t.heading}</h1>
        <p>${t.body}</p>
        <p><a href="mailto:${to}">${to}</a></p>
        <p><a href="${t.home}">${t.back}</a></p>
      </div>
    </div>
  </section>
</main>
</body>
</html>`;
  return new Response(html, {
    status,
    headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" },
  });
}

export async function onRequestPost({ request, env }) {
  const url = new URL(request.url);

  let form;
  try {
    form = await request.formData();
  } catch {
    return problem(url, "en", 400);
  }

  const lang = form.get("lang") === "sr" ? "sr" : "en";
  const email = String(form.get("email") || "").trim();
  const message = String(form.get("message") || "").trim();
  const topic = String(form.get("topic") || "other");
  const trap = String(form.get("company") || "").trim();
  const done = new URL(lang === "sr" ? "/sr/sent/" : "/sent/", url);

  // A bot filled the hidden field. Accept it so it learns nothing, send nothing.
  if (trap) return Response.redirect(done.toString(), 303);

  if (!EMAIL.test(email) || message.length < 5 || message.length > 5000) {
    return problem(url, lang, 400);
  }

  if (!env.RESEND_API_KEY || !env.RESEND_FROM || !env.CONTACT_TO) {
    return problem(url, lang, 500);
  }

  const label = TOPICS[topic] || TOPICS.other;
  const text = [
    `From: ${email}`,
    `Topic: ${label}`,
    `Page: ${lang}`,
    "",
    message,
  ].join("\n");

  let sent;
  try {
    sent = await fetch(ENDPOINT, {
      method: "POST",
      headers: {
        authorization: `Bearer ${env.RESEND_API_KEY}`,
        "content-type": "application/json",
      },
      body: JSON.stringify({
        from: env.RESEND_FROM,
        to: [env.CONTACT_TO],
        reply_to: email,
        subject: `worldbytouch.com – ${label} – ${email}`,
        text,
      }),
    });
  } catch {
    return problem(url, lang, 502);
  }

  if (!sent.ok) return problem(url, lang, 502);

  return Response.redirect(done.toString(), 303);
}

// Someone who lands on the endpoint directly gets the page, not an error.
export async function onRequestGet({ request }) {
  return Response.redirect(new URL("/", new URL(request.url)).toString(), 302);
}
