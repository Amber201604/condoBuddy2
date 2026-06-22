import React, { useEffect, useState } from "react";
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  TextInput, Modal, RefreshControl,
} from "react-native";
import { listPackages, pickupPackage } from "../api/client";

export default function PackageScreen() {
  const [packages, setPackages] = useState<any[]>([]);
  const [modalVisible, setModalVisible] = useState(false);
  const [selectedPkg, setSelectedPkg] = useState<any>(null);
  const [code, setCode] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    setRefreshing(true);
    try {
      const res = await listPackages();
      setPackages(res.data);
    } finally { setRefreshing(false); }
  };

  useEffect(() => { load(); }, []);

  const handlePickup = async () => {
    if (!selectedPkg || !code) return;
    try {
      await pickupPackage(selectedPkg.id, code);
      setModalVisible(false);
      setCode("");
      load();
    } catch (e) {}
  };

  const statusColor: Record<string, string> = {
    received: "#f0a500", notified: "#3498db", picked_up: "#2ecc71", returned: "#95a5a6",
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>📦 Packages</Text>
      </View>

      <ScrollView refreshControl={<RefreshControl refreshing={refreshing} onRefresh={load} />}>
        {packages.map((pkg) => (
          <View key={pkg.id} style={styles.card}>
            <View style={styles.cardHeader}>
              <Text style={styles.cardTitle}>{pkg.description || pkg.tracking_number || "Package"}</Text>
              <View style={[styles.badge, { backgroundColor: statusColor[pkg.status] || "#888" }]}>
                <Text style={styles.badgeText}>{pkg.status}</Text>
              </View>
            </View>
            <Text style={styles.cardDetail}>📬 {pkg.carrier || "Unknown carrier"}</Text>
            {pkg.locker_number && (
              <Text style={styles.cardDetail}>🔐 Locker: {pkg.locker_number}</Text>
            )}
            {pkg.status !== "picked_up" && (
              <TouchableOpacity
                style={styles.pickupBtn}
                onPress={() => { setSelectedPkg(pkg); setModalVisible(true); }}
              >
                <Text style={styles.pickupBtnText}>Pick Up</Text>
              </TouchableOpacity>
            )}
          </View>
        ))}
      </ScrollView>

      <Modal visible={modalVisible} animationType="slide" transparent>
        <View style={styles.overlay}>
          <View style={styles.modal}>
            <Text style={styles.modalTitle}>Pick Up Package</Text>
            <Text style={styles.modalDesc}>Enter your locker access code</Text>
            <TextInput
              style={styles.input}
              placeholder="Access Code"
              placeholderTextColor="#888"
              keyboardType="number-pad"
              value={code}
              onChangeText={setCode}
            />
            <TouchableOpacity style={styles.submitBtn} onPress={handlePickup}>
              <Text style={styles.submitBtnText}>Confirm Pickup</Text>
            </TouchableOpacity>
            <TouchableOpacity onPress={() => setModalVisible(false)}>
              <Text style={styles.cancelText}>Cancel</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#1a1a2e" },
  header: { padding: 16, paddingTop: 50 },
  title: { fontSize: 22, fontWeight: "bold", color: "#fff" },
  card: { backgroundColor: "#16213e", marginHorizontal: 16, marginBottom: 10, borderRadius: 12, padding: 14, borderWidth: 1, borderColor: "#0f3460" },
  cardHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 6 },
  cardTitle: { fontSize: 15, fontWeight: "bold", color: "#fff", flex: 1 },
  badge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4 },
  badgeText: { color: "#fff", fontSize: 10, fontWeight: "bold" },
  cardDetail: { color: "#a0a0a0", fontSize: 13, marginBottom: 2 },
  pickupBtn: { backgroundColor: "#e94560", borderRadius: 8, padding: 10, alignItems: "center", marginTop: 8 },
  pickupBtnText: { color: "#fff", fontWeight: "bold" },
  overlay: { flex: 1, backgroundColor: "#000000cc", justifyContent: "center", padding: 20 },
  modal: { backgroundColor: "#16213e", borderRadius: 16, padding: 20 },
  modalTitle: { fontSize: 18, fontWeight: "bold", color: "#fff", marginBottom: 4 },
  modalDesc: { color: "#a0a0a0", marginBottom: 12 },
  input: { backgroundColor: "#0f3460", borderRadius: 8, padding: 12, color: "#fff", marginBottom: 10 },
  submitBtn: { backgroundColor: "#e94560", borderRadius: 8, padding: 14, alignItems: "center", marginTop: 10 },
  submitBtnText: { color: "#fff", fontWeight: "bold" },
  cancelText: { color: "#888", textAlign: "center", marginTop: 12 },
});
