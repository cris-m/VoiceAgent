import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { useGetVoicesQuery } from '@/services/voice';
import { useGetPersonalitiesQuery } from '@/services/personality';

export interface Voice {
  id: string;
  name: string;
  language?: string;
  gender?: string | null;
  description?: string | null;
  preview_text?: string | null;
  tags?: string[] | null;
}

export interface Personality {
  id: string;
  name: string;
  description?: string | null;
  preview_text?: string | null;
  tags?: string[] | null;
  is_default?: boolean;
}

export interface VoiceConfigMessage {
  type: 'config';
  voice_id: string | null;
  personality_id: string | null;
  speed: number | null;
  language: string | null;
}

type Broadcaster = (config: VoiceConfigMessage) => void;

interface VoiceConfigContextValue {
  voices: Voice[];
  personalities: Personality[];
  selectedVoiceId: string | null;
  selectedPersonalityId: string | null;
  speed: number;
  language: string;
  isLoadingVoices: boolean;
  isLoadingPersonalities: boolean;
  setVoiceId: (id: string) => void;
  setPersonalityId: (id: string) => void;
  setSpeed: (s: number) => void;
  setLanguage: (l: string) => void;
  setBroadcaster: (fn: Broadcaster | null) => void;
  getCurrentConfig: () => VoiceConfigMessage;
}

const LS_VOICE_KEY = 'voiceagent:selected_voice';
const LS_PERSONALITY_KEY = 'voiceagent:selected_personality';
const LS_SPEED_KEY = 'voiceagent:speed';
const LS_LANGUAGE_KEY = 'voiceagent:language';

const VoiceConfigContext = createContext<VoiceConfigContextValue | null>(null);

export function VoiceConfigProvider({ children }: { children: ReactNode }) {
  const [selectedVoiceId, setSelectedVoiceIdState] = useState<string | null>(() =>
    typeof window !== 'undefined' ? localStorage.getItem(LS_VOICE_KEY) : null,
  );
  const [selectedPersonalityId, setSelectedPersonalityIdState] = useState<string | null>(() =>
    typeof window !== 'undefined' ? localStorage.getItem(LS_PERSONALITY_KEY) : null,
  );
  const [speed, setSpeedState] = useState<number>(() => {
    const v = typeof window !== 'undefined' ? localStorage.getItem(LS_SPEED_KEY) : null;
    const n = v ? parseFloat(v) : NaN;
    return Number.isFinite(n) && n > 0 ? n : 1.0;
  });
  const [language, setLanguageState] = useState<string>(() =>
    (typeof window !== 'undefined' && localStorage.getItem(LS_LANGUAGE_KEY)) || 'auto',
  );

  const { data: voicesData, isLoading: isLoadingVoices } = useGetVoicesQuery();
  const { data: personalitiesData, isLoading: isLoadingPersonalities } =
    useGetPersonalitiesQuery();

  const voices: Voice[] = useMemo(() => voicesData?.voices ?? [], [voicesData]);
  const personalities: Personality[] = useMemo(
    () => personalitiesData?.personalities ?? [],
    [personalitiesData],
  );

  const broadcasterRef = useRef<Broadcaster | null>(null);

  useEffect(() => {
    if (!voicesData) return;
    setSelectedVoiceIdState((current) => {
      if (current && voicesData.voices.some((v) => v.id === current)) return current;
      return voicesData.default_voice ?? voicesData.voices[0]?.id ?? null;
    });
  }, [voicesData]);

  useEffect(() => {
    if (!personalitiesData) return;
    setSelectedPersonalityIdState((current) => {
      if (current && personalitiesData.personalities.some((p) => p.id === current)) {
        return current;
      }
      return personalitiesData.default_id ?? personalitiesData.personalities[0]?.id ?? null;
    });
  }, [personalitiesData]);

  const getCurrentConfig = useCallback(
    (): VoiceConfigMessage => ({
      type: 'config',
      voice_id: selectedVoiceId,
      personality_id: selectedPersonalityId,
      speed,
      language,
    }),
    [selectedVoiceId, selectedPersonalityId, speed, language],
  );

  const setVoiceId = useCallback(
    (id: string) => {
      setSelectedVoiceIdState(id);
      if (typeof window !== 'undefined') localStorage.setItem(LS_VOICE_KEY, id);
      broadcasterRef.current?.({
        type: 'config',
        voice_id: id,
        personality_id: selectedPersonalityId,
        speed,
        language,
      });
    },
    [selectedPersonalityId, speed, language],
  );

  const setPersonalityId = useCallback(
    (id: string) => {
      setSelectedPersonalityIdState(id);
      if (typeof window !== 'undefined') localStorage.setItem(LS_PERSONALITY_KEY, id);
      broadcasterRef.current?.({
        type: 'config',
        voice_id: selectedVoiceId,
        personality_id: id,
        speed,
        language,
      });
    },
    [selectedVoiceId, speed, language],
  );

  const setSpeed = useCallback(
    (s: number) => {
      setSpeedState(s);
      if (typeof window !== 'undefined') localStorage.setItem(LS_SPEED_KEY, String(s));
      broadcasterRef.current?.({
        type: 'config',
        voice_id: selectedVoiceId,
        personality_id: selectedPersonalityId,
        speed: s,
        language,
      });
    },
    [selectedVoiceId, selectedPersonalityId, language],
  );

  const setLanguage = useCallback(
    (l: string) => {
      setLanguageState(l);
      if (typeof window !== 'undefined') localStorage.setItem(LS_LANGUAGE_KEY, l);
      broadcasterRef.current?.({
        type: 'config',
        voice_id: selectedVoiceId,
        personality_id: selectedPersonalityId,
        speed,
        language: l,
      });
    },
    [selectedVoiceId, selectedPersonalityId, speed],
  );

  const setBroadcaster = useCallback((fn: Broadcaster | null) => {
    broadcasterRef.current = fn;
  }, []);

  const value = useMemo<VoiceConfigContextValue>(
    () => ({
      voices,
      personalities,
      selectedVoiceId,
      selectedPersonalityId,
      speed,
      language,
      isLoadingVoices,
      isLoadingPersonalities,
      setVoiceId,
      setPersonalityId,
      setSpeed,
      setLanguage,
      setBroadcaster,
      getCurrentConfig,
    }),
    [
      voices,
      personalities,
      selectedVoiceId,
      selectedPersonalityId,
      speed,
      language,
      isLoadingVoices,
      isLoadingPersonalities,
      setVoiceId,
      setPersonalityId,
      setSpeed,
      setLanguage,
      setBroadcaster,
      getCurrentConfig,
    ],
  );

  return (
    <VoiceConfigContext.Provider value={value}>{children}</VoiceConfigContext.Provider>
  );
}

export function useVoiceConfig(): VoiceConfigContextValue {
  const ctx = useContext(VoiceConfigContext);
  if (!ctx) throw new Error('useVoiceConfig must be used within a VoiceConfigProvider');
  return ctx;
}
