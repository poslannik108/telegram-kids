// Telegram Kids — мобильное приложение для ребёнка
// React Native (Android + iOS)

import React, { useEffect, useState } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { StatusBar, View, ActivityIndicator } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import Icon from 'react-native-vector-icons/MaterialIcons';

import ChatsScreen from './screens/ChatsScreen';
import MessagesScreen from './screens/MessagesScreen';
import ContactsScreen from './screens/ContactsScreen';
import SettingsScreen from './screens/SettingsScreen';
import LoginScreen from './screens/LoginScreen';
import PendingScreen from './screens/PendingScreen';
import AwaitingLinkScreen from './screens/AwaitingLinkScreen';

const Stack = createStackNavigator();
const Tab = createBottomTabNavigator();

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        tabBarStyle: { backgroundColor: '#17212b' },
        tabBarActiveTintColor: '#5288c1',
        tabBarInactiveTintColor: '#aaaaaa',
        headerStyle: { backgroundColor: '#17212b' },
        headerTintColor: '#ffffff',
      }}
    >
      <Tab.Screen
        name="Chats"
        component={ChatsScreen}
        options={{
          title: 'Чаты',
          tabBarIcon: ({ color }) => <Icon name="chat" size={24} color={color} />,
        }}
      />
      <Tab.Screen
        name="Contacts"
        component={ContactsScreen}
        options={{
          title: 'Контакты',
          tabBarIcon: ({ color }) => <Icon name="people" size={24} color={color} />,
        }}
      />
      <Tab.Screen
        name="Settings"
        component={SettingsScreen}
        options={{
          title: 'Настройки',
          tabBarIcon: ({ color }) => <Icon name="settings" size={24} color={color} />,
        }}
      />
    </Tab.Navigator>
  );
}

export default function App() {
  const [initialRoute, setInitialRoute] = useState(null); // null = загрузка

  useEffect(() => {
    AsyncStorage.getItem('child_token').then(token => {
      setInitialRoute(token ? 'Main' : 'Login');
    });
  }, []);

  if (!initialRoute) {
    return (
      <View style={{ flex: 1, backgroundColor: '#17212b', justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator size="large" color="#5288c1" />
      </View>
    );
  }

  return (
    <NavigationContainer>
      <StatusBar barStyle="light-content" backgroundColor="#17212b" />
      <Stack.Navigator
        initialRouteName={initialRoute}
        screenOptions={{
          headerStyle: { backgroundColor: '#17212b' },
          headerTintColor: '#ffffff',
        }}
      >
        <Stack.Screen
          name="Login"
          component={LoginScreen}
          options={{ headerShown: false }}
        />
        <Stack.Screen
          name="AwaitingLink"
          component={AwaitingLinkScreen}
          options={{ headerShown: false }}
        />
        <Stack.Screen
          name="Main"
          component={MainTabs}
          options={{ headerShown: false }}
        />
        <Stack.Screen
          name="Messages"
          component={MessagesScreen}
          options={{ title: 'Сообщения' }}
        />
        <Stack.Screen
          name="Pending"
          component={PendingScreen}
          options={{ title: 'Ожидает разрешения' }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
