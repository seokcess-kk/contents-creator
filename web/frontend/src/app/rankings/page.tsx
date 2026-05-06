// P1: /rankings 본체는 / 로 승격됨. 외부 북마크/SEO 보호 위해 영구 redirect.
import { permanentRedirect } from "next/navigation";

export default function RankingsRedirectPage(): never {
  permanentRedirect("/");
}
