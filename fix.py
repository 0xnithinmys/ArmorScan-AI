import sys

path = 'frontend/src/app/scans/page.tsx'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

fix = """    });
    if (!r.ok) throw new Error(await readError(r));
    if (r.status === 204) return undefined as T;
    return (await r.json()) as T;
  }
 
  const load = useCallback(async () => {
    if (!isLoaded) return;
    if (!token) { setIsLoading(false); return; }
    try {
      const [t, s] = await Promise.all([
        apiFetch<Target[]>("/targets/"),
        apiFetch<Scan[]>("/scans/"),
      ]);
      setTargets(t); setScans(s);
      setSelectedId(prev => prev || s[0]?.id || "");
    } finally {
      setIsLoading(false);
    }
  }, [token, isLoaded]);
 
  useEffect(() => { load().catch(e => setError(e.message)); }, [load]);

  useEffect(() => {
    if (!selectedId || !token) return;"""

c = c.replace('    const wsBase = API_BASE.replace', fix + '\n    const wsBase = API_BASE.replace')

with open(path, 'w', encoding='utf-8') as f:
    f.write(c)
