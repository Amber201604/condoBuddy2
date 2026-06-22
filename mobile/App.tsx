import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { createStackNavigator } from "@react-navigation/stack";
import { Text } from "react-native";

import { useAuthStore } from "./src/store/auth";
import LoginScreen from "./src/components/LoginScreen";
import HomeScreen from "./src/screens/HomeScreen";
import WorkOrderScreen from "./src/screens/WorkOrderScreen";
import VisitorScreen from "./src/screens/VisitorScreen";
import AccessScreen from "./src/screens/AccessScreen";
import PackageScreen from "./src/screens/PackageScreen";
import FacilityBookingScreen from "./src/screens/FacilityBookingScreen";

const Tab = createBottomTabNavigator();
const Stack = createStackNavigator();

function TabIcon({ label, focused }: { label: string; focused: boolean }) {
  return (
    <Text style={{ fontSize: 20, opacity: focused ? 1 : 0.5 }}>
      {label}
    </Text>
  );
}

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused }) => {
          const icons: Record<string, string> = {
            Home: "🏠",
            WorkOrders: "🔧",
            Visitors: "🚶",
            Access: "🔑",
            Packages: "📦",
            Facilities: "📅",
          };
          return <TabIcon label={icons[route.name] || "•"} focused={focused} />;
        },
        tabBarActiveTintColor: "#e94560",
        tabBarInactiveTintColor: "#888",
        headerStyle: { backgroundColor: "#1a1a2e" },
        headerTintColor: "#fff",
      })}
    >
      <Tab.Screen name="Home" component={HomeScreen} />
      <Tab.Screen name="WorkOrders" component={WorkOrderScreen} />
      <Tab.Screen name="Visitors" component={VisitorScreen} />
      <Tab.Screen name="Access" component={AccessScreen} />
      <Tab.Screen name="Packages" component={PackageScreen} />
      <Tab.Screen name="Facilities" component={FacilityBookingScreen} />
    </Tab.Navigator>
  );
}

export default function App() {
  const token = useAuthStore((s) => s.token);

  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {token ? (
          <Stack.Screen name="Main" component={MainTabs} />
        ) : (
          <Stack.Screen name="Login" component={LoginScreen} />
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
