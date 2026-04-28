"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import BrandMediaLibrary from "@/components/BrandMediaLibrary";
import BrandRegisterDialog from "@/components/BrandRegisterDialog";
import BrandSourceUpload from "@/components/BrandSourceUpload";
import {
  listBrands,
  listSources,
  type BrandMessageSource,
  type BrandProfile,
} from "@/lib/brand-studio-api";

export default function BrandStudioListPage() {
  const [brands, setBrands] = useState<BrandProfile[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeBrand, setActiveBrand] = useState<BrandProfile | null>(null);
  const [activeSources, setActiveSources] = useState<BrandMessageSource[]>([]);
  const [sourcesLoading, setSourcesLoading] = useState(false);
  const [showRegister, setShowRegister] = useState(false);
  const [mediaBrand, setMediaBrand] = useState<BrandProfile | null>(null);

  const refresh = useCallback(async () => {
    try {
      setError(null);
      setBrands(await listBrands());
    } catch (err) {
      setError(err instanceof Error ? err.message : "브랜드 목록 로드 실패");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function openSourcesDialog(brand: BrandProfile) {
    if (!brand.id) return;
    setActiveBrand(brand);
    setSourcesLoading(true);
    try {
      const items = await listSources(brand.id);
      setActiveSources(items);
    } catch (err) {
      setActiveSources([]);
      setError(err instanceof Error ? err.message : "sources 로드 실패");
    } finally {
      setSourcesLoading(false);
    }
  }

  function closeSourcesDialog() {
    setActiveBrand(null);
    setActiveSources([]);
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <Link href="/" className="text-sm text-blue-700 hover:underline">
          ← 대시보드
        </Link>
        <h1 className="text-base font-bold text-gray-900">브랜드 스튜디오</h1>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">
            {brands?.length ?? 0} 브랜드
          </span>
          <button
            type="button"
            onClick={() => setShowRegister(true)}
            className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            + 신규 브랜드
          </button>
        </div>
      </div>

      {error && (
        <div className="text-xs text-red-700 border border-red-200 rounded p-2">
          {error}
        </div>
      )}

      {brands === null ? (
        <div className="text-sm text-gray-500">로딩 중…</div>
      ) : brands.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {brands.map((b) => (
            <BrandCard
              key={b.id ?? b.slug}
              brand={b}
              onOpenSources={() => openSourcesDialog(b)}
              onOpenMedia={() => setMediaBrand(b)}
            />
          ))}
        </div>
      )}

      {activeBrand && activeBrand.id && (
        <BrandSourceUpload
          brandId={activeBrand.id}
          brandName={activeBrand.name}
          existing={activeSources}
          onClose={closeSourcesDialog}
          onUploaded={(s) => setActiveSources((prev) => [...prev, s])}
        />
      )}

      {activeBrand && sourcesLoading && (
        <div className="fixed bottom-4 right-4 text-xs bg-gray-900 text-white px-2 py-1 rounded">
          sources 로드 중…
        </div>
      )}

      {showRegister && (
        <BrandRegisterDialog
          onClose={() => setShowRegister(false)}
          onCreated={(b) => {
            setBrands((prev) => (prev ? [b, ...prev] : [b]));
          }}
        />
      )}

      {mediaBrand && mediaBrand.id && (
        <BrandMediaLibrary
          brandId={mediaBrand.id}
          brandName={mediaBrand.name}
          onClose={() => setMediaBrand(null)}
        />
      )}
    </div>
  );
}

function BrandCard({
  brand,
  onOpenSources,
  onOpenMedia,
}: {
  brand: BrandProfile;
  onOpenSources: () => void;
  onOpenMedia: () => void;
}) {
  const created = brand.created_at
    ? new Date(brand.created_at).toLocaleDateString("ko-KR")
    : "-";
  return (
    <div className="border border-gray-200 rounded p-3 bg-white space-y-2">
      <div>
        <div className="text-sm font-semibold text-gray-900 truncate" title={brand.name}>
          {brand.name}
        </div>
        <div className="text-xs text-gray-500 truncate">{brand.slug}</div>
      </div>
      <div className="text-xs text-gray-600 space-y-0.5">
        <div className="truncate" title={brand.homepage_url}>
          🌐 {brand.homepage_url || "(URL 미등록)"}
        </div>
        <div>📅 {created}</div>
        <div>자산 v{brand.current_asset_version}</div>
      </div>
      <div className="flex flex-wrap gap-1.5 pt-1">
        {brand.id ? (
          <Link
            href={`/brand-studio/${encodeURIComponent(brand.id)}/new`}
            className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            카드 생성
          </Link>
        ) : (
          <span className="px-2 py-1 text-xs bg-gray-300 text-gray-600 rounded cursor-not-allowed">
            카드 생성 (id 없음)
          </span>
        )}
        <button
          type="button"
          onClick={onOpenSources}
          disabled={!brand.id}
          className="px-2 py-1 text-xs border border-gray-300 text-gray-700 rounded hover:bg-gray-50 disabled:opacity-50"
        >
          sources
        </button>
        <button
          type="button"
          onClick={onOpenMedia}
          disabled={!brand.id}
          className="px-2 py-1 text-xs border border-gray-300 text-gray-700 rounded hover:bg-gray-50 disabled:opacity-50"
        >
          미디어
        </button>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="border border-dashed border-gray-300 rounded p-6 text-center text-sm text-gray-600 space-y-1">
      <div className="font-semibold text-gray-800">등록된 브랜드가 없습니다</div>
      <div className="text-xs">
        우측 상단 <strong>+ 신규 브랜드</strong> 버튼으로 첫 브랜드를 등록하세요.
      </div>
    </div>
  );
}
