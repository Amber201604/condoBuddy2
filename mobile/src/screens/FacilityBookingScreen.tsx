import React, { useEffect, useState } from "react";
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  TextInput, Modal, RefreshControl, Alert,
} from "react-native";
import { listBookings, createBooking, listFacilities } from "../api/client";

const FACILITY_ICONS: Record<string, string> = {
  meeting_room: "💼", gym: "🏋️", party_room: "🎉", theatre: "🎬",
  bbq: "🍖", pool: "🏊", study_room: "📚", game_room: "🎮",
};

export default function FacilityBookingScreen() {
  const [bookings, setBookings] = useState<any[]>([]);
  const [facilities, setFacilities] = useState<any[]>([]);
  const [modalVisible, setModalVisible] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedFacility, setSelectedFacility] = useState<any>(null);
  const [form, setForm] = useState({
    facility_name: "", facility_type: "", start_time: "", end_time: "", notes: "", attendees_count: 1,
  });

  const load = async () => {
    setRefreshing(true);
    try {
      const [bRes, fRes] = await Promise.all([listBookings(), listFacilities()]);
      setBookings(bRes.data);
      setFacilities(fRes.data.facilities || []);
    } finally { setRefreshing(false); }
  };

  useEffect(() => { load(); }, []);

  const openBookingModal = (facility: any) => {
    setSelectedFacility(facility);
    setForm({
      facility_name: facility.name,
      facility_type: facility.type,
      start_time: "",
      end_time: "",
      notes: "",
      attendees_count: 1,
    });
    setModalVisible(true);
  };

  const submit = async () => {
    try {
      await createBooking(form);
      setModalVisible(false);
      load();
    } catch (e: any) {
      const message = e?.response?.data?.detail || e?.message || "Failed to create booking";
      Alert.alert("Booking Error", message);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>📅 Facility Booking</Text>
      </View>

      <Text style={styles.sectionTitle}>Available Facilities</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.facilityScroll}>
        {facilities.map((f) => (
          <TouchableOpacity key={f.name} style={styles.facilityCard} onPress={() => openBookingModal(f)}>
            <Text style={styles.facilityIcon}>{FACILITY_ICONS[f.type] || "🏢"}</Text>
            <Text style={styles.facilityName}>{f.name}</Text>
            <Text style={styles.facilityMeta}>Cap: {f.capacity}  •  {f.floor}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <Text style={styles.sectionTitle}>My Bookings</Text>
      <ScrollView refreshControl={<RefreshControl refreshing={refreshing} onRefresh={load} />}>
        {bookings.map((b) => (
          <View key={b.id} style={styles.bookingCard}>
            <View style={styles.bookingHeader}>
              <Text style={styles.bookingName}>{b.facility_name}</Text>
              <View style={[styles.statusBadge, { backgroundColor: b.status === "confirmed" ? "#2ecc71" : b.status === "pending" ? "#f0a500" : "#e94560" }]}>
                <Text style={styles.statusText}>{b.status}</Text>
              </View>
            </View>
            <Text style={styles.bookingTime}>
              {new Date(b.start_time).toLocaleString()} → {new Date(b.end_time).toLocaleTimeString()}
            </Text>
            <Text style={styles.bookingMeta}>👥 {b.attendees_count} attendees</Text>
          </View>
        ))}
      </ScrollView>

      <Modal visible={modalVisible} animationType="slide" transparent>
        <View style={styles.overlay}>
          <View style={styles.modal}>
            <Text style={styles.modalTitle}>
              Book {selectedFacility?.name}
            </Text>
            <TextInput
              style={styles.input}
              placeholder="Start Time (ISO 8601)"
              placeholderTextColor="#888"
              value={form.start_time}
              onChangeText={(t) => setForm({ ...form, start_time: t })}
            />
            <TextInput
              style={styles.input}
              placeholder="End Time (ISO 8601)"
              placeholderTextColor="#888"
              value={form.end_time}
              onChangeText={(t) => setForm({ ...form, end_time: t })}
            />
            <TextInput
              style={styles.input}
              placeholder="Attendees"
              placeholderTextColor="#888"
              keyboardType="number-pad"
              value={String(form.attendees_count)}
              onChangeText={(t) => setForm({ ...form, attendees_count: parseInt(t) || 1 })}
            />
            <TextInput
              style={styles.input}
              placeholder="Notes"
              placeholderTextColor="#888"
              value={form.notes}
              onChangeText={(t) => setForm({ ...form, notes: t })}
              multiline
            />
            <TouchableOpacity style={styles.submitBtn} onPress={submit}>
              <Text style={styles.submitBtnText}>Book Now</Text>
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
  sectionTitle: { fontSize: 16, fontWeight: "bold", color: "#fff", paddingHorizontal: 16, marginTop: 16, marginBottom: 8 },
  facilityScroll: { paddingLeft: 16, maxHeight: 140 },
  facilityCard: {
    backgroundColor: "#16213e",
    borderRadius: 12,
    padding: 14,
    marginRight: 10,
    width: 130,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#0f3460",
  },
  facilityIcon: { fontSize: 28, marginBottom: 6 },
  facilityName: { color: "#fff", fontWeight: "bold", fontSize: 13, textAlign: "center" },
  facilityMeta: { color: "#888", fontSize: 11, marginTop: 2 },
  bookingCard: {
    backgroundColor: "#16213e",
    marginHorizontal: 16,
    marginBottom: 10,
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: "#0f3460",
  },
  bookingHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 6 },
  bookingName: { fontSize: 15, fontWeight: "bold", color: "#fff", flex: 1 },
  statusBadge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4 },
  statusText: { color: "#fff", fontSize: 10, fontWeight: "bold" },
  bookingTime: { color: "#a0a0a0", fontSize: 12, marginBottom: 2 },
  bookingMeta: { color: "#888", fontSize: 11 },
  overlay: { flex: 1, backgroundColor: "#000000cc", justifyContent: "center", padding: 20 },
  modal: { backgroundColor: "#16213e", borderRadius: 16, padding: 20 },
  modalTitle: { fontSize: 18, fontWeight: "bold", color: "#fff", marginBottom: 16 },
  input: { backgroundColor: "#0f3460", borderRadius: 8, padding: 12, color: "#fff", marginBottom: 10 },
  submitBtn: { backgroundColor: "#e94560", borderRadius: 8, padding: 14, alignItems: "center", marginTop: 10 },
  submitBtnText: { color: "#fff", fontWeight: "bold" },
  cancelText: { color: "#888", textAlign: "center", marginTop: 12 },
});
