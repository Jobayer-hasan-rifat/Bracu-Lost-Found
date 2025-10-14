import React, { memo, useEffect, useState } from 'react';
import { 
  Box, 
  Typography, 
  Container, 
  Grid, 
  Card, 
  CardContent, 
  Button 
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import DirectionsCarIcon from '@mui/icons-material/DirectionsCar';
import TwoWheelerIcon from '@mui/icons-material/TwoWheeler';
import StoreIcon from '@mui/icons-material/Store';
import PersonIcon from '@mui/icons-material/Person';
import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettings';
import HowToRegIcon from '@mui/icons-material/HowToReg';
import FacebookIcon from '@mui/icons-material/Facebook';
import GitHubIcon from '@mui/icons-material/GitHub';
import ScrollingAnnouncement from '../components/ScrollingAnnouncement';
import notificationService from '../services/notificationService';

// Memoized service card component for better performance
const ServiceCard = memo(({ service, isLoggedIn, onServiceClick }) => (
  <Card 
    className="custom-card service-card"
    sx={{ 
      height: '100%', 
      display: 'flex', 
      flexDirection: 'column',
      borderRadius: '16px',
      overflow: 'hidden',
      backgroundColor: service.color,
    }}
  >
    <Box sx={{ 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center',
      p: 3,
      backgroundColor: 'rgba(255, 255, 255, 0.7)'
    }}>
      {service.icon}
    </Box>
    <CardContent sx={{ flexGrow: 1, textAlign: 'center' }}>
      <Typography gutterBottom variant="h5" component="h3" sx={{ fontWeight: 600 }}>
        {service.title}
      </Typography>
      <Typography sx={{ mb: 2 }}>
        {service.description}
      </Typography>
      <Button 
        variant="contained" 
        onClick={() => onServiceClick(service.path)}
        className="gradient-primary"
        sx={{ 
          mt: 2,
          borderRadius: '20px',
          px: 3
        }}
      >
        {isLoggedIn ? 'Access Now' : 'Login to Access'}
      </Button>
    </CardContent>
  </Card>
));

const Home = () => {
  const navigate = useNavigate();
  const isLoggedIn = localStorage.getItem('token');
  const [announcements, setAnnouncements] = useState([]);
  const [loading, setLoading] = useState(false);

  // Add animation classes when component mounts
  useEffect(() => {
    const elements = document.querySelectorAll('.animate-on-mount');
    elements.forEach((element, index) => {
      setTimeout(() => {
        element.classList.add('slide-up');
      }, index * 100);
    });
  }, []);

  // Fetch announcements for the home page
  useEffect(() => {
    const fetchAnnouncements = async () => {
      try {
        setLoading(true);
        const data = await notificationService.getPageAnnouncements('home');
        if (Array.isArray(data)) {
          setAnnouncements(data);
        }
      } catch (error) {
        console.error('Error fetching announcements:', error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchAnnouncements();
    
    // Set up a polling interval to refresh announcements periodically
    const intervalId = setInterval(fetchAnnouncements, 30000); // Refresh every 30 seconds
    
    // Clean up interval on component unmount
    return () => clearInterval(intervalId);
  }, []);

  const handleServiceClick = (path) => {
    if (isLoggedIn) {
      navigate(path);
    } else {
      navigate('/login');
    }
  };

  const navigateTo = (path) => {
    navigate(path);
  };

  const services = [
    {
      title: 'Lost & Found',
      description: 'Report or find lost items around the campus.',
      icon: <TwoWheelerIcon sx={{ fontSize: 70, color: '#2e7d32' }} />,
      path: '/lost-found',
      color: '#c8e6c9'
    },
    {
      title: 'Marketplace',
      description: 'Buy, sell, or exchange books, notes, and other items.',
      icon: <StoreIcon sx={{ fontSize: 70, color: '#c62828' }} />,
      path: '/marketplace',
      color: '#ffcdd2'
    },
    {
      title: 'Ride Sharing',
      description: 'Find or offer rides to and from campus with fellow students.',
      icon: <DirectionsCarIcon sx={{ fontSize: 70, color: '#1565c0' }} />,
      path: '/ride-booking',
      color: '#bbdefb'
    }
  ];

  return (
    <Box sx={{ 
      flexGrow: 1, 
      minHeight: '100vh',
      background: 'linear-gradient(to bottom, #e1f5fe, #ffffff)'
    }}>
      {/* Display announcements at the top of the page */}
      {announcements && announcements.length > 0 && (
        <Container maxWidth="lg" sx={{ pt: 2 }}>
          <ScrollingAnnouncement 
            announcements={announcements} 
            page="home" 
          />
        </Container>
      )}
      {/* Banner Section */}
      <Box sx={{ 
        py: { xs: 5, md: 8 }, 
        background: 'linear-gradient(135deg, #1a237e 0%, #283593 50%, #303f9f 100%)',
        color: 'white',
        textAlign: 'center',
        borderRadius: { xs: '0 0 10% 10%', md: '0 0 20% 20%' },
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.2)'
      }}>
        <Container maxWidth="lg">
          <Typography 
            variant="h2" 
            component="h1"
            className="animate-on-mount fade-in" 
            sx={{ 
              fontWeight: 700,
              fontSize: { xs: '2rem', sm: '3rem', md: '3.5rem' },
              textShadow: '1px 1px 3px rgba(0, 0, 0, 0.4)',
              mb: 2
            }}
          >
            BRACU EUREKA
          </Typography>
          <Typography 
            variant="h5" 
            component="p"
            className="animate-on-mount fade-in"
            sx={{ 
              maxWidth: '800px', 
              mx: 'auto',
              opacity: 0.9,
              fontSize: { xs: '1rem', md: '1.25rem' }
            }}
          >
            Your one-stop platform for all campus services
          </Typography>
          
          {/* Authentication Buttons */}
          <Box sx={{ mt: 4, display: 'flex', justifyContent: 'center', gap: 2, flexWrap: 'wrap' }}>
            <Button
              variant="contained"
              color="primary"
              size="large"
              startIcon={<PersonIcon />}
              onClick={() => {
                const userData = localStorage.getItem('user');
                if (isLoggedIn && userData) {
                  navigateTo('/profile');
                } else {
                  navigateTo('/login');
                }
              }}
              className="animate-on-mount"
              sx={{ borderRadius: '20px', px: 3, py: 1.2, backgroundColor: '#1565c0' }}
            >
              {(() => {
                const userData = localStorage.getItem('user');
                return (isLoggedIn && userData) ? `Hi, ${JSON.parse(userData).name}` : 'Student Login';
              })()}
            </Button>
            <Button
              variant="contained"
              color="secondary"
              size="large"
              startIcon={<HowToRegIcon />}
              onClick={() => navigateTo('/register')}
              className="animate-on-mount"
              sx={{ borderRadius: '20px', px: 3, py: 1.2, backgroundColor: '#7b1fa2' }}
            >
              Register
            </Button>
            <Button
              variant="contained"
              color="error"
              size="large"
              startIcon={<AdminPanelSettingsIcon />}
              onClick={() => navigateTo('/admin-login')}
              className="animate-on-mount"
              sx={{ borderRadius: '20px', px: 3, py: 1.2, backgroundColor: '#c62828' }}
            >
              Admin Login
            </Button>
          </Box>
        </Container>
      </Box>

      {/* Services Section */}
      <Container maxWidth="lg" sx={{ py: { xs: 4, md: 6 } }}>
        <Typography 
          variant="h4" 
          component="h2"
          className="animate-on-mount"
          sx={{ 
            textAlign: 'center', 
            mb: { xs: 3, md: 5 }, 
            fontWeight: 600,
            color: '#263238'
          }}
        >
          Campus Services
        </Typography>

        <Grid container spacing={3} justifyContent="center">
          {services.map((service, index) => (
            <Grid item xs={12} sm={6} md={4} key={index} className="animate-on-mount">
              <ServiceCard 
                service={service} 
                isLoggedIn={isLoggedIn} 
                onServiceClick={handleServiceClick} 
              />
            </Grid>
          ))}
        </Grid>
      </Container>

      {/* About Us Footer */}
      <Box component="footer" sx={{
        background: 'linear-gradient(90deg, #283593 0%, #1565c0 100%)',
        color: 'white',
        py: 5,
        mt: 8,
        borderTopLeftRadius: '30px',
        borderTopRightRadius: '30px',
        boxShadow: '0 -4px 24px rgba(21,101,192,0.12)'
      }}>
        <Container maxWidth="lg">
          <Typography variant="h5" sx={{ fontWeight: 700, mb: 3, textAlign: 'center', letterSpacing: 1 }}>
            About the Creator
          </Typography>
          <Grid container spacing={4} justifyContent="center">
            {/* Creator Profile */}
            <Grid item xs={12} sm={6} md={4} sx={{ textAlign: 'center' }}>
              <Box 
                component="img"
                src="/assets/images/IMG_2345.jpg"
                alt="Md. Jobayer Hasan"
                sx={{ 
                  width: 120, 
                  height: 120, 
                  borderRadius: '50%', 
                  border: '3px solid #fff', 
                  margin: '0 auto 16px auto',
                  objectFit: 'cover'
                }} 
              />
              <Typography variant="h6" sx={{ fontWeight: 600 }}>Md. Jobayer Hasan</Typography>
              <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mt: 1 }}>
                <a href="https://www.facebook.com/jobayerhasan.rifat" target="_blank" rel="noopener noreferrer" style={{ color: 'white' }}>
                  <FacebookIcon fontSize="large" />
                </a>
                <a href="https://github.com/Jobayer-hasan-rifat" target="_blank" rel="noopener noreferrer" style={{ color: 'white' }}>
                  <GitHubIcon fontSize="large" />
                </a>
              </Box>
            </Grid>
          </Grid>
          <Typography variant="body2" sx={{ textAlign: 'center', mt: 4, opacity: 0.8 }}>
            &copy; {new Date().getFullYear()} BRACU Eureka. All rights reserved.
          </Typography>
        </Container>
      </Box>
    </Box>
  );
};

export default memo(Home);