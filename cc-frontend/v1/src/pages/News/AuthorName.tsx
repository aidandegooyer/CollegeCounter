// The post's author, linking to their profile (e.g. Twitter) when the post has one
function AuthorName({
  author,
  authorLink,
  className = "",
}: {
  author?: string;
  authorLink?: string;
  className?: string;
}) {
  const name = author || "College Counter Staff";
  if (!authorLink) return <span className={className}>{name}</span>;

  // Sanity links are sometimes saved without a scheme (e.g. "x.com/handle")
  const href = /^https?:\/\//i.test(authorLink)
    ? authorLink
    : `https://${authorLink}`;
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={`${className} hover:text-blue-400 hover:underline`}
    >
      {name}
    </a>
  );
}

export default AuthorName;
