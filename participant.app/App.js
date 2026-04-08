import React, { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Linking,
  Pressable,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { LinearGradient } from "expo-linear-gradient";
import { api } from "./src/api";
import {
  API_BASE,
  MODULE_ORDER,
  PARTICIPANT_CARD_COPY,
  PARTICIPANT_DEFAULTS,
} from "./src/config";

const TOKEN_KEY = "creatro_participant_token";

function resolveTheme(me) {
  const agencyTheme = me?.agency_theme || {};
  const projectTheme = me?.project_theme || {};
  const useProjectTheme = Boolean(projectTheme.enabled);

  return {
    base: useProjectTheme
      ? projectTheme.base_color || PARTICIPANT_DEFAULTS.agencyBase
      : agencyTheme.base_color || PARTICIPANT_DEFAULTS.agencyBase,
    primary: useProjectTheme
      ? projectTheme.primary_color || PARTICIPANT_DEFAULTS.projectPrimary
      : agencyTheme.primary_color || PARTICIPANT_DEFAULTS.agencyPrimary,
    secondary: useProjectTheme
      ? projectTheme.secondary_color || PARTICIPANT_DEFAULTS.projectSecondary
      : agencyTheme.secondary_color || PARTICIPANT_DEFAULTS.agencySecondary,
  };
}

function resolveBranding(me) {
  const agencyName = me?.agency_name || PARTICIPANT_DEFAULTS.fallbackAgencyName;
  const projectName = me?.active_project_name || PARTICIPANT_DEFAULTS.fallbackProjectName;
  const projectVisual = me?.project_visual_name || me?.meeting_visual_name || projectName;
  const activeLogoLabel = me?.project_logo_name || me?.agency_logo_name || agencyName;
  const sponsorName = me?.main_sponsor_name || PARTICIPANT_DEFAULTS.fallbackSponsorName;
  const footerBanner = me?.project_footer_banner_name || projectName;

  return {
    agencyName,
    projectName,
    projectVisual,
    activeLogoLabel,
    sponsorName,
    footerBanner,
  };
}

function ScreenShell({ theme, eyebrow, title, subtitle, rightText, footerText, children }) {
  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: theme.base }]}>
      <StatusBar barStyle="light-content" />
      <View style={styles.screen}>
        <LinearGradient
          colors={[theme.base, theme.primary, theme.secondary]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={styles.hero}
        >
          <View style={styles.heroTopRow}>
            <Text style={styles.heroEyebrow}>{eyebrow}</Text>
            {rightText ? <Text style={styles.heroCode}>{rightText}</Text> : null}
          </View>
          <Text style={styles.heroTitle}>{title}</Text>
          {subtitle ? <Text style={styles.heroSubtitle}>{subtitle}</Text> : null}
        </LinearGradient>
        <View style={styles.content}>{children}</View>
        {footerText ? (
          <View style={styles.footerBanner}>
            <Text style={styles.footerBannerText}>{footerText}</Text>
          </View>
        ) : null}
      </View>
    </SafeAreaView>
  );
}

function LoginView({ loading, onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const theme = resolveTheme(null);
  const branding = resolveBranding(null);

  return (
    <ScreenShell
      theme={theme}
      eyebrow={PARTICIPANT_DEFAULTS.appName}
      title={"Kat\u0131l\u0131mc\u0131 Uygulamas\u0131"}
      subtitle={
        "Acente logosu varsay\u0131lan gelir. Alt proje g\u00f6rseli tan\u0131ml\u0131ysa login ve header alan\u0131nda onu kullan\u0131r."
      }
      rightText={PARTICIPANT_DEFAULTS.loginHeroCode}
      footerText={`${branding.projectName} Banner`}
    >
      <View style={styles.logoCard}>
        <View style={[styles.logoBadge, { borderColor: `${theme.secondary}80` }]}>
          <Text style={styles.logoBadgeText}>{branding.activeLogoLabel}</Text>
        </View>
        <Text style={styles.logoHint}>
          {"Tema \u00f6nceli\u011fi acente renkleri. Proje tema renkleri tan\u0131ml\u0131ysa onlar \u00fcst\u00fcne yazar."}
        </Text>
      </View>

      <View style={styles.panel}>
        <Text style={styles.panelTitle}>{"Giri\u015f"}</Text>
        <Text style={styles.panelBody}>
          {"Hesab\u0131n\u0131zla oturum a\u00e7\u0131n. Proje se\u00e7ildi\u011finde toplant\u0131, rezervasyon ve duyuru ak\u0131\u015f\u0131 a\u00e7\u0131lacakt\u0131r."}
        </Text>
        <TextInput
          style={styles.input}
          autoCapitalize="none"
          placeholder={"Kullan\u0131c\u0131 ad\u0131"}
          placeholderTextColor="#7C8CA5"
          value={username}
          onChangeText={setUsername}
        />
        <TextInput
          style={styles.input}
          secureTextEntry
          placeholder={"\u015eifre"}
          placeholderTextColor="#7C8CA5"
          value={password}
          onChangeText={setPassword}
        />
        <Pressable
          style={[styles.primaryBtn, loading && styles.btnDisabled]}
          disabled={loading}
          onPress={() => onLogin(username.trim(), password)}
        >
          <Text style={styles.primaryBtnText}>
            {loading ? "Giri\u015f yap\u0131l\u0131yor" : "Giri\u015f Yap"}
          </Text>
        </Pressable>
        <Text style={styles.footnote}>API: {API_BASE}</Text>
      </View>
    </ScreenShell>
  );
}

function ProjectSelectView({ token, onSelected, me }) {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const theme = resolveTheme(me);
  const branding = resolveBranding(me);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const list = await api.projects(token);
        if (!active) return;
        setProjects((list || []).filter((item) => item && item.is_active));
      } catch (err) {
        Alert.alert("Proje Hatas\u0131", err.message);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [token]);

  return (
    <ScreenShell
      theme={theme}
      eyebrow={branding.agencyName}
      title={"Aktif Proje Se\u00e7imi"}
      subtitle={
        "Kat\u0131l\u0131mc\u0131 aray\u00fcz\u00fc proje bazl\u0131 a\u00e7\u0131l\u0131r. Acente logosu veya proje g\u00f6rseli se\u00e7ime g\u00f6re \u00fcstte g\u00f6sterilir."
      }
      rightText={me?.role ? String(me.role).toUpperCase() : "PROJECT"}
      footerText={`${branding.footerBanner} Footer`}
    >
      <View style={styles.panel}>
        <Text style={styles.panelTitle}>Proje Listesi</Text>
        <Text style={styles.panelBody}>
          {"Se\u00e7im yapt\u0131\u011f\u0131n\u0131z anda participant ak\u0131\u015f\u0131 a\u00e7\u0131l\u0131r."}
        </Text>
        {loading ? (
          <View style={styles.loaderWrap}>
            <ActivityIndicator size="large" color={theme.base} />
          </View>
        ) : (
          <ScrollView showsVerticalScrollIndicator={false} style={styles.projectList}>
            {projects.map((project) => (
              <Pressable
                key={project.id}
                style={styles.projectCard}
                onPress={() => onSelected(project.id)}
              >
                <Text style={styles.projectCode}>{project.operation_code || "-"}</Text>
                <Text style={styles.projectName}>{project.name || "Ads\u0131z Proje"}</Text>
                <Text style={styles.projectMeta}>{"Projeyi aktifle\u015ftir"}</Text>
              </Pressable>
            ))}
          </ScrollView>
        )}
      </View>
    </ScreenShell>
  );
}

function ActionCard({ title, body, meta, onPress, span = "half" }) {
  return (
    <Pressable style={[styles.actionCard, span === "full" && styles.actionCardFull]} onPress={onPress}>
      <Text style={styles.actionCardTitle}>{title}</Text>
      <Text style={styles.actionCardBody}>{body}</Text>
      <Text style={styles.actionCardMeta}>{meta}</Text>
    </Pressable>
  );
}

function HomeView({ me, onLogout }) {
  const theme = resolveTheme(me);
  const branding = resolveBranding(me);
  const modules = useMemo(() => {
    const visible = Array.isArray(me?.visible_modules) ? me.visible_modules : [];
    const keyed = new Map(visible.map((item) => [item.key, item]));
    const ordered = [];

    MODULE_ORDER.forEach((key) => {
      const item = keyed.get(key);
      if (item) ordered.push(item);
    });

    visible.forEach((item) => {
      if (!MODULE_ORDER.includes(item.key)) ordered.push(item);
    });

    return ordered;
  }, [me]);

  const moduleByKey = useMemo(() => new Map(modules.map((item) => [item.key, item])), [modules]);

  const openModuleByKey = async (key, fallbackPath) => {
    const href = moduleByKey.get(key)?.href || fallbackPath;
    if (!href) {
      Alert.alert("Mod\u00fcl Yok", "Bu alan hen\u00fcz ba\u011flanmad\u0131.");
      return;
    }
    const url = `${API_BASE}${href}`;
    try {
      const supported = await Linking.canOpenURL(url);
      if (!supported) throw new Error(url);
      await Linking.openURL(url);
    } catch (err) {
      Alert.alert("Ba\u011flant\u0131 A\u00e7\u0131lamad\u0131", err.message || url);
    }
  };

  const openReservationArea = async () => {
    if (moduleByKey.get("konaklama")) {
      await openModuleByKey("konaklama", "/konaklama-ui");
      return;
    }
    if (moduleByKey.get("transfer")) {
      await openModuleByKey("transfer", "/transfer-ui");
      return;
    }
    Alert.alert(
      "Rezervasyonlar\u0131m",
      "Transfer veya konaklama ba\u011flant\u0131s\u0131 hen\u00fcz tan\u0131ml\u0131 de\u011fil.",
    );
  };

  const sponsorThankYouNote =
    "QR okutuldu\u011funda transfer i\u00e7in transfer sponsoru; kay\u0131t veya konaklama i\u00e7in ilgili sponsor te\u015fekk\u00fcr g\u00f6rseli a\u00e7\u0131lacak.";

  return (
    <ScreenShell
      theme={theme}
      eyebrow={branding.activeLogoLabel}
      title={branding.projectName}
      subtitle={
        "Toplant\u0131 odakl\u0131 participant aray\u00fcz\u00fc. Hero kartta Toplant\u0131 Mod\u00fcl\u00fc, alt akslarda rezervasyon ve duyuru alanlar\u0131 var."
      }
      rightText={me?.active_project_code || "ACTIVE"}
      footerText={`${branding.footerBanner} Footer`}
    >
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent}>
        <View style={styles.identityCard}>
          <View style={styles.identityMain}>
            <Text style={styles.identityLabel}>{"Acente / Proje G\u00f6rseli"}</Text>
            <Text style={styles.identityTitle}>{branding.activeLogoLabel}</Text>
            <Text style={styles.identityHint}>
              {"Acente logosu varsay\u0131lan. Alt proje g\u00f6rseli tan\u0131ml\u0131ysa header ve login taraf\u0131nda onu g\u00f6ster."}
            </Text>
          </View>
          <View
            style={[
              styles.sponsorBadge,
              { borderColor: `${theme.primary}45`, backgroundColor: `${theme.secondary}26` },
            ]}
          >
            <Text style={styles.sponsorBadgeEyebrow}>ANA SPONSOR</Text>
            <Text style={styles.sponsorBadgeText}>{branding.sponsorName}</Text>
          </View>
        </View>

        <Pressable
          style={[
            styles.heroModuleCard,
            { backgroundColor: theme.base, borderColor: `${theme.primary}55` },
          ]}
          onPress={() => openModuleByKey("toplanti", "/toplanti-ui")}
        >
          <View style={styles.heroVisual}>
            <Text style={styles.heroVisualEyebrow}>{"Toplant\u0131 G\u00f6rseli"}</Text>
            <Text style={styles.heroVisualTitle}>{branding.projectVisual}</Text>
          </View>
          <View style={styles.heroModuleContent}>
            <Text style={[styles.heroModuleLabel, { color: theme.secondary }]}>
              {"Toplant\u0131 Mod\u00fcl\u00fc"}
            </Text>
            <Text style={styles.heroModuleTitle}>{PARTICIPANT_CARD_COPY.oturumlar}</Text>
            <Text style={styles.heroModuleBody}>
              {"Orta hero kartta oturumlar a\u00e7\u0131l\u0131r. Alttaki alt kartlar program ak\u0131\u015f\u0131, bildiriler, sertifikalar ve kurslar i\u00e7in ayr\u0131ld\u0131."}
            </Text>
          </View>
        </Pressable>

        <View style={styles.featureGrid}>
          <ActionCard
            title={PARTICIPANT_CARD_COPY.program}
            body={"G\u00fcn i\u00e7i ak\u0131\u015f\u0131 ve salon zamanlar\u0131."}
            meta={"Toplant\u0131"}
            onPress={() => openModuleByKey("toplanti", "/toplanti-ui")}
          />
          <ActionCard
            title={PARTICIPANT_CARD_COPY.bildiriler}
            body={"Sunum ve bildiri i\u00e7eriklerine giri\u015f."}
            meta={"Toplant\u0131"}
            onPress={() => openModuleByKey("toplanti", "/toplanti-ui")}
          />
          <ActionCard
            title={PARTICIPANT_CARD_COPY.kurslar}
            body={"Kurs listesi ve uygun kay\u0131t ak\u0131\u015f\u0131."}
            meta={"Toplant\u0131"}
            onPress={() => openModuleByKey("toplanti", "/toplanti-ui")}
          />
          <ActionCard
            title={PARTICIPANT_CARD_COPY.sertifikalar}
            body={"Kat\u0131l\u0131m ve kurs sertifika alanlar\u0131."}
            meta={"Toplant\u0131"}
            onPress={() => openModuleByKey("toplanti", "/toplanti-ui")}
          />
        </View>

        <View style={styles.sectionHead}>
          <Text style={styles.sectionTitle}>{"Kat\u0131l\u0131mc\u0131 Alanlar\u0131"}</Text>
          <Text style={styles.sectionMeta}>{`${modules.length} eri\u015fim alan\u0131`}</Text>
        </View>

        <View style={styles.featureGrid}>
          <ActionCard
            title={PARTICIPANT_CARD_COPY.rezervasyonlarim}
            body={"Transfer ve konaklama detaylar\u0131n\u0131 g\u00f6r, gerekirse de\u011fi\u015fiklik iste."}
            meta="Transfer + Konaklama"
            onPress={openReservationArea}
            span="full"
          />
          <ActionCard
            title={PARTICIPANT_CARD_COPY.duyurular}
            body={"Kongre duyurular\u0131, acil mesajlar ve son bilgilendirmeler."}
            meta="Duyurular"
            onPress={() => openModuleByKey("duyurular", "/duyurular-ui")}
          />
          <ActionCard
            title={PARTICIPANT_CARD_COPY.qr}
            body={sponsorThankYouNote}
            meta="QR + Sponsor"
            onPress={() => openModuleByKey("toplanti", "/toplanti-ui")}
          />
        </View>

        <View style={styles.summaryCard}>
          <Text style={styles.summaryTitle}>{"Kat\u0131l\u0131mc\u0131 \u00d6zeti"}</Text>
          <View style={styles.summaryRow}>
            <Text style={styles.summaryLabel}>{"Kullan\u0131c\u0131"}</Text>
            <Text style={styles.summaryValue}>{me?.username || "-"}</Text>
          </View>
          <View style={styles.summaryRow}>
            <Text style={styles.summaryLabel}>Rol</Text>
            <Text style={styles.summaryValue}>{me?.role || "participant"}</Text>
          </View>
          <View style={styles.summaryRow}>
            <Text style={styles.summaryLabel}>Aktif Proje</Text>
            <Text style={styles.summaryValue}>{me?.active_project_code || "-"}</Text>
          </View>
          <View style={styles.summaryRow}>
            <Text style={styles.summaryLabel}>{"Tema \u00d6nceli\u011fi"}</Text>
            <Text style={styles.summaryValue}>Acente, varsa Proje</Text>
          </View>
        </View>

        <Pressable style={styles.secondaryBtn} onPress={onLogout}>
          <Text style={styles.secondaryBtnText}>{"\u00c7\u0131k\u0131\u015f Yap"}</Text>
        </Pressable>
      </ScrollView>
    </ScreenShell>
  );
}

export default function App() {
  const [token, setToken] = useState("");
  const [me, setMe] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authBusy, setAuthBusy] = useState(false);

  const loadMe = async (accessToken) => {
    const profile = await api.me(accessToken);
    setMe(profile);
    return profile;
  };

  useEffect(() => {
    (async () => {
      try {
        const stored = await AsyncStorage.getItem(TOKEN_KEY);
        if (!stored) {
          setLoading(false);
          return;
        }
        setToken(stored);
        await loadMe(stored);
      } catch (_) {
        await AsyncStorage.removeItem(TOKEN_KEY);
        setToken("");
        setMe(null);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const handleLogin = async (username, password) => {
    if (!username || !password) {
      Alert.alert("Eksik Bilgi", "Kullan\u0131c\u0131 ad\u0131 ve \u015fifre gerekli.");
      return;
    }
    setAuthBusy(true);
    try {
      const out = await api.login(username, password);
      const accessToken = out.access_token;
      await AsyncStorage.setItem(TOKEN_KEY, accessToken);
      setToken(accessToken);
      setMe(out.user || null);
    } catch (err) {
      Alert.alert("Giri\u015f Hatas\u0131", err.message);
    } finally {
      setAuthBusy(false);
    }
  };

  const handleProjectSelect = async (projectId) => {
    try {
      await api.setActiveProject(token, projectId);
      await loadMe(token);
    } catch (err) {
      Alert.alert("Proje Hatas\u0131", err.message);
    }
  };

  const handleLogout = async () => {
    await AsyncStorage.removeItem(TOKEN_KEY);
    setToken("");
    setMe(null);
  };

  const needsProject = me && !me.active_project_id && me.role !== "superadmin";

  if (loading) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.loaderScreen}>
          <ActivityIndicator size="large" color="#FFFFFF" />
          <Text style={styles.loaderText}>{"Y\u00fckleniyor"}</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (!token) {
    return <LoginView loading={authBusy} onLogin={handleLogin} />;
  }

  if (needsProject) {
    return <ProjectSelectView token={token} me={me} onSelected={handleProjectSelect} />;
  }

  if (me) {
    return <HomeView me={me} onLogout={handleLogout} />;
  }

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.loaderScreen}>
        <ActivityIndicator size="large" color="#FFFFFF" />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: "#081634",
  },
  screen: {
    flex: 1,
    backgroundColor: "#EFF4FF",
  },
  hero: {
    paddingHorizontal: 20,
    paddingTop: 18,
    paddingBottom: 26,
  },
  heroTopRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 16,
  },
  heroEyebrow: {
    color: "#CFE8FF",
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 0.8,
    textTransform: "uppercase",
  },
  heroCode: {
    color: "#DDEEFF",
    fontSize: 11,
    fontWeight: "700",
  },
  heroTitle: {
    color: "#FFFFFF",
    fontSize: 28,
    fontWeight: "800",
    lineHeight: 34,
  },
  heroSubtitle: {
    marginTop: 8,
    color: "#DBEAFE",
    fontSize: 14,
    lineHeight: 20,
  },
  content: {
    flex: 1,
    paddingHorizontal: 16,
    paddingTop: 16,
  },
  footerBanner: {
    borderTopWidth: 1,
    borderTopColor: "#D8E2F2",
    backgroundColor: "#FFFFFF",
    paddingHorizontal: 18,
    paddingVertical: 12,
  },
  footerBannerText: {
    color: "#4F6483",
    fontSize: 12,
    fontWeight: "700",
    textAlign: "center",
  },
  logoCard: {
    borderRadius: 18,
    borderWidth: 1,
    borderColor: "#D9E6F7",
    backgroundColor: "#F6FAFF",
    padding: 18,
    marginBottom: 14,
  },
  logoBadge: {
    borderRadius: 14,
    borderWidth: 1,
    backgroundColor: "#FFFFFF",
    paddingHorizontal: 14,
    paddingVertical: 18,
    alignItems: "center",
  },
  logoBadgeText: {
    color: "#102B59",
    fontSize: 18,
    fontWeight: "800",
  },
  logoHint: {
    marginTop: 10,
    color: "#60708A",
    fontSize: 13,
    lineHeight: 18,
  },
  panel: {
    backgroundColor: "#FFFFFF",
    borderRadius: 18,
    borderWidth: 1,
    borderColor: "#D7E2F0",
    padding: 18,
    shadowColor: "#0A1024",
    shadowOpacity: 0.08,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 10 },
    elevation: 2,
  },
  panelTitle: {
    color: "#081634",
    fontSize: 20,
    fontWeight: "800",
    marginBottom: 8,
  },
  panelBody: {
    color: "#5C6B82",
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 14,
  },
  input: {
    height: 50,
    borderWidth: 1,
    borderColor: "#D4DDEB",
    borderRadius: 12,
    backgroundColor: "#F7FAFF",
    paddingHorizontal: 14,
    fontSize: 15,
    color: "#0A1024",
    marginBottom: 10,
  },
  primaryBtn: {
    marginTop: 8,
    height: 50,
    borderRadius: 12,
    backgroundColor: "#0A1024",
    alignItems: "center",
    justifyContent: "center",
  },
  primaryBtnText: {
    color: "#FFFFFF",
    fontSize: 15,
    fontWeight: "800",
  },
  secondaryBtn: {
    marginTop: 18,
    height: 48,
    borderRadius: 12,
    backgroundColor: "#CFD9E8",
    alignItems: "center",
    justifyContent: "center",
  },
  secondaryBtnText: {
    color: "#0A1024",
    fontSize: 14,
    fontWeight: "800",
  },
  btnDisabled: {
    opacity: 0.72,
  },
  footnote: {
    marginTop: 12,
    color: "#6E7D96",
    fontSize: 12,
  },
  loaderScreen: {
    flex: 1,
    backgroundColor: "#081634",
    alignItems: "center",
    justifyContent: "center",
  },
  loaderText: {
    marginTop: 10,
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "600",
  },
  loaderWrap: {
    paddingVertical: 24,
    alignItems: "center",
    justifyContent: "center",
  },
  projectList: {
    maxHeight: 420,
  },
  projectCard: {
    borderWidth: 1,
    borderColor: "#D6E0EE",
    borderRadius: 14,
    padding: 14,
    backgroundColor: "#F8FBFF",
    marginBottom: 10,
  },
  projectCode: {
    color: "#0F2858",
    fontSize: 13,
    fontWeight: "800",
    marginBottom: 4,
  },
  projectName: {
    color: "#081634",
    fontSize: 16,
    fontWeight: "700",
    marginBottom: 6,
  },
  projectMeta: {
    color: "#56708F",
    fontSize: 12,
    fontWeight: "700",
  },
  scrollContent: {
    paddingBottom: 22,
  },
  identityCard: {
    flexDirection: "row",
    gap: 12,
    alignItems: "stretch",
    marginBottom: 16,
  },
  identityMain: {
    flex: 1,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: "#D7E2F0",
    backgroundColor: "#FFFFFF",
    padding: 16,
  },
  identityLabel: {
    color: "#637690",
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 0.3,
    textTransform: "uppercase",
  },
  identityTitle: {
    color: "#081634",
    fontSize: 18,
    fontWeight: "800",
    marginTop: 8,
  },
  identityHint: {
    color: "#60708A",
    fontSize: 13,
    lineHeight: 18,
    marginTop: 8,
  },
  sponsorBadge: {
    width: 122,
    borderRadius: 18,
    borderWidth: 1,
    padding: 14,
    alignItems: "center",
    justifyContent: "center",
  },
  sponsorBadgeEyebrow: {
    color: "#60708A",
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 0.4,
  },
  sponsorBadgeText: {
    marginTop: 8,
    color: "#0F2858",
    fontSize: 15,
    fontWeight: "800",
    textAlign: "center",
  },
  heroModuleCard: {
    borderRadius: 24,
    borderWidth: 1,
    overflow: "hidden",
    marginBottom: 16,
  },
  heroVisual: {
    minHeight: 132,
    paddingHorizontal: 18,
    paddingVertical: 18,
    justifyContent: "flex-end",
    backgroundColor: "#133D83",
  },
  heroVisualEyebrow: {
    color: "#B9DFFF",
    fontSize: 11,
    fontWeight: "700",
    textTransform: "uppercase",
  },
  heroVisualTitle: {
    marginTop: 8,
    color: "#FFFFFF",
    fontSize: 22,
    fontWeight: "800",
  },
  heroModuleContent: {
    backgroundColor: "#FFFFFF",
    paddingHorizontal: 18,
    paddingVertical: 16,
  },
  heroModuleLabel: {
    fontSize: 11,
    fontWeight: "800",
    textTransform: "uppercase",
    letterSpacing: 0.4,
  },
  heroModuleTitle: {
    marginTop: 6,
    color: "#081634",
    fontSize: 24,
    fontWeight: "800",
  },
  heroModuleBody: {
    marginTop: 8,
    color: "#60708A",
    fontSize: 14,
    lineHeight: 20,
  },
  featureGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    gap: 12,
    marginBottom: 16,
  },
  actionCard: {
    width: "48.2%",
    borderRadius: 18,
    borderWidth: 1,
    borderColor: "#D7E2F0",
    backgroundColor: "#FFFFFF",
    padding: 16,
    minHeight: 138,
  },
  actionCardFull: {
    width: "100%",
    minHeight: 122,
  },
  actionCardTitle: {
    color: "#081634",
    fontSize: 16,
    fontWeight: "800",
  },
  actionCardBody: {
    marginTop: 8,
    color: "#60708A",
    fontSize: 13,
    lineHeight: 18,
  },
  actionCardMeta: {
    marginTop: "auto",
    color: "#113876",
    fontSize: 12,
    fontWeight: "800",
  },
  sectionHead: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },
  sectionTitle: {
    color: "#081634",
    fontSize: 18,
    fontWeight: "800",
  },
  sectionMeta: {
    color: "#62738E",
    fontSize: 12,
    fontWeight: "700",
  },
  summaryCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 18,
    borderWidth: 1,
    borderColor: "#D7E2F0",
    padding: 18,
    marginBottom: 6,
  },
  summaryTitle: {
    color: "#081634",
    fontSize: 18,
    fontWeight: "800",
    marginBottom: 12,
  },
  summaryRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: "#EEF3FA",
  },
  summaryLabel: {
    color: "#60708A",
    fontSize: 13,
    fontWeight: "600",
  },
  summaryValue: {
    color: "#081634",
    fontSize: 13,
    fontWeight: "800",
    maxWidth: "55%",
    textAlign: "right",
  },
});
