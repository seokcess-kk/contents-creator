// P1: /pipeline 의 "단계별 흐름 시각화" 사용자 의도는 운영 홈 (/) 에 흡수.
// 외부 북마크/SEO 보호 위해 영구 redirect (P3·P5 후속에서 운영 홈 안 별도 섹션 또는 /queue MetricStrip 으로 통합 검토).
import { permanentRedirect } from "next/navigation";

export default function PipelineRedirectPage(): never {
  permanentRedirect("/");
}
