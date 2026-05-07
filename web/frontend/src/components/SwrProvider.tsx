"use client";

// 운영 OS 의 데이터 페칭은 SWR 로 통일. 기본값은 보수적으로 잡는다.
//   - revalidateOnFocus: 탭 복귀 시 자동 재검증 (운영 화면 신선도 유지)
//   - dedupingInterval: 같은 키 5초 중복 요청 합치기
//   - errorRetryCount: 2회까지만 재시도 (BFF 게이트가 503 일 때 무한 재시도 방지)
//
// 글로벌 mutate("key") 로 외부에서도 재검증 가능.

import { SWRConfig } from "swr";

export default function SwrProvider({ children }: { children: React.ReactNode }) {
  return (
    <SWRConfig
      value={{
        revalidateOnFocus: true,
        revalidateOnReconnect: true,
        dedupingInterval: 5000,
        errorRetryCount: 2,
        shouldRetryOnError: true,
      }}
    >
      {children}
    </SWRConfig>
  );
}
