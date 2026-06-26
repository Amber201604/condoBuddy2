import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  RefreshControl,
  Alert,
} from "react-native";
import { useAuthStore } from "../store/auth";
import { listWorkOrders, listPackages, listVisitors } from "../api/client";
import { connectWebSocket } from "../api/client";

export default function HomeScreen() {
  const user = useAuthStore((s) => s.user);
  const token = useAuthStore((s) => s.token);
  const [stats, setStats] = useState({ wo: 0, pkg: 0, visitors: 0 });
  const [refreshing, setRefreshing] = useState(false);
  const [notifications, setNotifications] = useState<string[]>([]);

  const [loadError, setLoadError] = useState<string | null>(null);

  const loadStats = async () => {
    try {
      setLoadError(null);
      const [woRes, pkgRes, visRes] = await Promise.all([
        listWorkOrders({ status: "open" }),
        listPackages({ status: "notified" }),
        listVisitors({ status: "scheduled" }),
      ]);
      setStats({
        wo: woRes.data.length,
        pkg: pkgRes.data.length,
        visitors: visRes.data.length,
      });
    } catch (e: any) {
      const message = e?.response?.data?.detail || e?.message || "Failed to load dashboard data";
      setLoadError(message);
      console.error("HomeScreen loadStats error:", e);
    }
  };

  useEffect(() => {
    loadStats();
    if (!token) return;
    const ws = connectWebSocket(token);
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === "notification") {
        setNotifications((prev) => [msg.data.title, ...prev].slice(0, 5));
      }
    };
    return () => ws.close();
  }, [token]);

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={loadStats} />
      }
    >
      <View style={styles.header}>
        <Text style={styles.greeting}>Hey, {user?.full_name || "Resident"} 🖤</Text>
        <Text style={styles.unit}>Unit {user?.unit_number || "—"}</Text>
      </View>

      {loadError && (
        <View style={styles.errorBanner}>
          <Text style={styles.errorText}>{loadError}</Text>
        </View>
      )}

      <View style={styles.statsRow}>
        <StatCard label="Open Work Orders" value={stats.wo} icon="🔧" />
        <StatCard label="Packages" value={stats.pkg} icon="📦" />
        <StatCard label="Visitors" value={stats.visitors} icon="🚶" />
      </View>

      {notifications.length > 0 && (
        <View style={styles.notifBox}>
          <Text style={styles.notifTitle}>🔔 Latest</Text>
          {notifications.map((n, i) => (
            <Text key={i} style={styles.notifItem}>• {n}</Text>
          ))}
        </View>
      )}

      <View style={styles.quickActions}>
        <Text style={styles.sectionTitle}>Quick Actions</Text>
        <TouchableOpacity style={styles.actionBtn}>
          <Text style={styles.actionText}>🚪 NFC Open Door</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.actionBtn}>
          <Text style={styles.actionText}>🛗 Call Elevator</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.actionBtn}>
          <Text style={styles.actionText}>📅 Book Facility</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

function StatCard({ label, value, icon }: { label: string; value: number; icon: string }) {
  return (
    <View style={styles.statCard}>
      <Text style={styles.statIcon}>{icon}</Text>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#1a1a2e" },
  header: { padding: 20, paddingTop: 50 },
  greeting: { fontSize: 24, fontWeight: "bold", color: "#fff" },
  unit: { fontSize: 14, color: "#a0a0a0", marginTop: 4 },
  statsRow: { flexDirection: "row", paddingHorizontal: 16, gap: 10 },
  statCard: {
    flex: 1,
    backgroundColor: "#16213e",
    borderRadius: 12,
    padding: 14,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#0f3460",
  },
  statIcon: { fontSize: 24 },
  statValue: { fontSize: 22, fontWeight: "bold", color: "#e94560", marginTop: 4 },
  statLabel: { fontSize: 11, color: "#a0a0a0", marginTop: 2, textAlign: "center" },
  notifBox: {
    margin: 16,
    backgroundColor: "#16213e",
    borderRadius: 12,
    padding: 16,
    borderLeftWidth: 4,
    borderLeftColor: "#e94560",
  },
  notifTitle: { fontSize: 14, fontWeight: "bold", color: "#e94560", marginBottom: 8 },
  notifItem: { fontSize: 13, color: "#ccc", marginBottom: 4 },
  quickActions: { padding: 16 },
  sectionTitle: { fontSize: 16, fontWeight: "bold", color: "#fff", marginBottom: 12 },
  actionBtn: {
    backgroundColor: "#0f3460",
    borderRadius: 10,
    padding: 16,
    marginBottom: 10,
  },
  actionText: { color: "#fff", fontSize: 15 },
  errorBanner: {
    margin: 16,
    backgroundColor: "#3d1a1a",
    borderRadius: 8,
    padding: 12,
    borderLeftWidth: 4,
    borderLeftColor: "#e94560",
  },
  errorText: { color: "#ff6b6b", fontSize: 13 },
});
