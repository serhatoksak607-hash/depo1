import React, { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Linking,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { StatusBar } from "expo-status-bar";
import { api } from "./src/api";
import { API_BASE, MODULE_LABELS } from "./src/config";

const TOKEN_KEY = "creatro_mobile_token";

function LoginView({ loading, onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  return (
    <View style={styles.card}>
      <Text style={styles.title}>Creatro Mobile</Text>
      <TextInput
        style={styles.input}
        autoCapitalize="none"
        placeholder="Kullanıcı adı"
        value={username}
        onChangeText={setUsername}
      />
      <TextInput
        style={styles.input}
        secureTextEntry
        placeholder="Şifre"
        value={password}
        onChangeText={setPassword}
      />
      <Pressable
        style={styles.primaryBtn}
        disabled={loading}
        onPress={() => onLogin(username, password)}
      >
        <Text style={styles.primaryBtnText}>{loading ? "Giriş..." : "Giriş Yap"}</Text>
      </Pressable>
      <Text style={styles.note}>
        API: {API_BASE}
      </Text>
    </View>
  );
}

function ProjectSelectView({ token, onSelected }) {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const list = await api.projects(token);
        if (active) setProjects((list || []).filter((p) => p.is_active));
      } catch (err) {
        Alert.alert("Proje Hatası", err.message);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [token]);

  if (loading) return <ActivityIndicator size="large" color="#0A1024" />;

  return (
    <View style={styles.card}>
      <Text style={styles.title}>Aktif Proje Seç</Text>
      <ScrollView style={{ maxHeight: 360 }}>
        {projects.map((p) => (
          <Pressable
            key={p.id}
            style={styles.rowBtn}
            onPress={() => onSelected(p.id)}
          >
            <Text style={styles.rowBtnTitle}>{p.operation_code}</Text>
            <Text style={styles.rowBtnSub}>{p.name}</Text>
          </Pressable>
        ))}
      </ScrollView>
    </View>
  );
}

function HomeView({ me, onLogout }) {
  const modules = useMemo(() => me.visible_modules || [], [me.visible_modules]);

  const openModule = async (href) => {
    const url = `${API_BASE}${href}`;
    const ok = await Linking.canOpenURL(url);
    if (!ok) return Alert.alert("Açılamadı", url);
    await Linking.openURL(url);
  };

  return (
    <View style={styles.card}>
      <Text style={styles.title}>Hoş geldin, {me.username}</Text>
      <Text style={styles.meta}>Rol: {me.role}</Text>
      <Text style={styles.meta}>
        Proje: {me.active_project_code || "-"} / {me.active_project_name || "-"}
      </Text>

      <View style={{ marginTop: 14 }}>
        {modules.map((m, idx) => (
          <Pressable
            key={`${m.key}-${idx}`}
            style={styles.moduleBtn}
            onPress={() => openModule(m.href)}
          >
            <Text style={styles.moduleBtnText}>
              {MODULE_LABELS[m.key] || m.key}
            </Text>
          </Pressable>
        ))}
      </View>

      <Pressable style={styles.logoutBtn} onPress={onLogout}>
        <Text style={styles.logoutText}>Çıkış Yap</Text>
      </Pressable>
    </View>
  );
}

export default function App() {
  const [token, setToken] = useState("");
  const [me, setMe] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authBusy, setAuthBusy] = useState(false);

  const loadMe = async (accessToken) => {
    const data = await api.me(accessToken);
    setMe(data);
    return data;
  };

  useEffect(() => {
    (async () => {
      try {
        const stored = await AsyncStorage.getItem(TOKEN_KEY);
        if (!stored) return;
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
    if (!username || !password) return Alert.alert("Eksik", "Kullanıcı adı ve şifre gerekli");
    setAuthBusy(true);
    try {
      const out = await api.login(username, password);
      const accessToken = out.access_token;
      await AsyncStorage.clear();
      await AsyncStorage.setItem(TOKEN_KEY, accessToken);
      setToken(accessToken);
      setMe(out.user || null);
    } catch (err) {
      Alert.alert("Giriş Hatası", err.message);
    } finally {
      setAuthBusy(false);
    }
  };

  const handleProjectSelect = async (projectId) => {
    try {
      await api.setActiveProject(token, projectId);
      await loadMe(token);
    } catch (err) {
      Alert.alert("Proje Hatası", err.message);
    }
  };

  const handleLogout = async () => {
    await AsyncStorage.clear();
    setToken("");
    setMe(null);
  };

  const needsProject = me && !me.active_project_id && me.role !== "superadmin";

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar style="light" />
      <View style={styles.container}>
        {loading ? (
          <ActivityIndicator size="large" color="#fff" />
        ) : !token ? (
          <LoginView loading={authBusy} onLogin={handleLogin} />
        ) : needsProject ? (
          <ProjectSelectView token={token} onSelected={handleProjectSelect} />
        ) : me ? (
          <HomeView me={me} onLogout={handleLogout} />
        ) : (
          <ActivityIndicator size="large" color="#fff" />
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#0A1024" },
  container: {
    flex: 1,
    justifyContent: "center",
    padding: 16,
    backgroundColor: "#0A1024",
  },
  card: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 16,
  },
  title: { fontSize: 20, fontWeight: "700", color: "#0A1024", marginBottom: 10 },
  input: {
    borderWidth: 1,
    borderColor: "#CBD5E1",
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginBottom: 10,
  },
  primaryBtn: {
    backgroundColor: "#0A1024",
    borderRadius: 8,
    paddingVertical: 12,
    alignItems: "center",
  },
  primaryBtnText: { color: "#fff", fontWeight: "700" },
  note: { marginTop: 8, color: "#64748B", fontSize: 12 },
  meta: { color: "#334155", marginBottom: 4 },
  moduleBtn: {
    backgroundColor: "#EEF4FF",
    borderColor: "#C9D8FF",
    borderWidth: 1,
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 12,
    marginBottom: 8,
  },
  moduleBtnText: { color: "#0A1024", fontWeight: "700" },
  logoutBtn: {
    marginTop: 12,
    backgroundColor: "#991B1B",
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: "center",
  },
  logoutText: { color: "#fff", fontWeight: "700" },
  rowBtn: {
    borderWidth: 1,
    borderColor: "#CBD5E1",
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
  },
  rowBtnTitle: { color: "#0A1024", fontWeight: "700" },
  rowBtnSub: { color: "#334155" },
});
