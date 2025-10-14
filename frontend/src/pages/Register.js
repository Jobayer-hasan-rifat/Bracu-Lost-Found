import React, { useState } from 'react';
import { 
  Box, 
  Typography, 
  TextField, 
  Button, 
  Container, 
  Paper, 
  Grid,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  CircularProgress,
  Alert,
  Link as MuiLink
} from '@mui/material';
import { Link, useNavigate } from 'react-router-dom';
import HowToRegIcon from '@mui/icons-material/HowToReg';
import axios from 'axios';

const Register = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    name: '',
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    student_id: '',
    department: '',
    semester: ''
  });
  const [idCardFile, setIdCardFile] = useState(null);
  const [idCardPreview, setIdCardPreview] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Using short forms of departments
  const departments = [
    'CSE',
    'EEE',
    'ARCH',
    'BBA',
    'PHARM',
    'ENH',
    'MNS',
    'ESS'
  ];

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value
    });
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setIdCardFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setIdCardPreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const validateForm = () => {
    // Validate required fields
    if (!formData.name || !formData.username || !formData.email || !formData.password || !formData.confirmPassword || 
        !formData.student_id || !formData.department || !formData.semester) {
      setError('Please fill in all required fields');
      return false;
    }
    
    // Validate email format
    if (!formData.email.endsWith('@g.bracu.ac.bd')) {
      setError('Please use your BRACU email (name@g.bracu.ac.bd)');
      return false;
    }
    
    // Validate password requirements
    const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?])[A-Za-z\d!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]{8,}$/;
    if (!passwordRegex.test(formData.password)) {
      setError('Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character');
      return false;
    }
    
    // Validate password match
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return false;
    }
    
    // Validate student ID
    if (formData.student_id.length !== 8 || isNaN(formData.student_id)) {
      setError('Student ID must be an 8-digit number');
      return false;
    }
    
    // Validate ID card upload
    if (!idCardFile) {
      setError('Please upload your ID card photo');
      return false;
    }
    
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setLoading(true);
    setError('');

    // Create form data for file upload
    const data = new FormData();
    Object.entries(formData).forEach(([key, value]) => {
      if (key !== 'confirmPassword') {
        data.append(key, value);
      }
    });
    data.append('id_card_photo', idCardFile);

    try {
      const response = await axios.post('/api/auth/register', data, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      setSuccess(response.data.message || 'Registration successful! Your account is pending approval.');
      setTimeout(() => {
        navigate('/login');
      }, 5000);
    } catch (err) {
      console.error('Registration error:', err);
      setError(err.response?.data?.error || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="md" sx={{ py: 8 }}>
      <Paper 
        elevation={3} 
        sx={{ 
          p: 4, 
          display: 'flex', 
          flexDirection: 'column', 
          alignItems: 'center',
          borderRadius: '16px',
          background: 'rgba(255, 255, 255, 0.85)',
          backdropFilter: 'blur(8px)',
          boxShadow: '0 8px 16px rgba(0, 0, 0, 0.1)',
          border: '1px solid rgba(255, 255, 255, 0.5)'
        }}
      >
        <Box sx={{ 
          background: 'linear-gradient(135deg, #7b1fa2, #6a1b9a)', 
          borderRadius: '50%', 
          p: 2, 
          mb: 2, 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center',
          boxShadow: '0 4px 8px rgba(0, 0, 0, 0.2)'
        }}>
          <HowToRegIcon sx={{ fontSize: 40, color: 'white' }} />
        </Box>
        
        <Typography component="h1" variant="h4" sx={{ mb: 3, fontWeight: 600, color: '#263238' }}>
          Student Registration
        </Typography>
        
        {success ? (
          <Alert severity="success" sx={{ width: '100%', mb: 2 }}>
            {success} Redirecting to login page...
          </Alert>
        ) : (
          <Box sx={{ width: '100%' }}>
            {error && <Alert severity="error" sx={{ width: '100%', mb: 2 }}>{error}</Alert>}
            
            <Box component="form" onSubmit={handleSubmit} sx={{ width: '100%' }}>
              <Grid container spacing={2}>
                {/* Personal Information */}
                <Grid item xs={12}>
                  <Typography variant="h6" color="primary" sx={{ mb: 1 }}>
                    Personal Information
                  </Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    required
                    fullWidth
                    id="name"
                    label="Full Name"
                    name="name"
                    autoComplete="name"
                    value={formData.name}
                    onChange={handleChange}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    required
                    fullWidth
                    id="username"
                    label="Username"
                    name="username"
                    autoComplete="username"
                    value={formData.username}
                    onChange={handleChange}
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    required
                    fullWidth
                    id="email"
                    label="BRACU Email Address"
                    name="email"
                    autoComplete="email"
                    placeholder="name@g.bracu.ac.bd"
                    value={formData.email}
                    onChange={handleChange}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    required
                    fullWidth
                    name="password"
                    label="Password"
                    type="password"
                    id="password"
                    autoComplete="new-password"
                    value={formData.password}
                    onChange={handleChange}
                    helperText="Must contain uppercase, lowercase, number and special character"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    required
                    fullWidth
                    name="confirmPassword"
                    label="Confirm Password"
                    type="password"
                    id="confirmPassword"
                    value={formData.confirmPassword}
                    onChange={handleChange}
                  />
                </Grid>

                {/* Academic Details */}
                <Grid item xs={12}>
                  <Typography variant="h6" color="primary" sx={{ mb: 1, mt: 2 }}>
                    Academic Details
                  </Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    required
                    fullWidth
                    id="student_id"
                    label="Student ID"
                    name="student_id"
                    placeholder="8-digit student ID"
                    value={formData.student_id}
                    onChange={handleChange}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth required>
                    <InputLabel id="department-label">Department</InputLabel>
                    <Select
                      labelId="department-label"
                      id="department"
                      name="department"
                      value={formData.department}
                      label="Department"
                      onChange={handleChange}
                    >
                      {departments.map((dept) => (
                        <MenuItem key={dept} value={dept}>
                          {dept}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    required
                    fullWidth
                      id="semester"
                    label="Current Semester"
                      name="semester"
                    placeholder="e.g., Spring 2023"
                      value={formData.semester}
                      onChange={handleChange}
                  />
                </Grid>

                {/* Verification */}
                <Grid item xs={12}>
                  <Typography variant="h6" color="primary" sx={{ mb: 1, mt: 2 }}>
                    ID Verification
                  </Typography>
                </Grid>
                <Grid item xs={12}>
                  <Typography variant="body1" gutterBottom>
                    Please upload a clear photo of your BRACU ID card. This will be used to verify your identity.
                  </Typography>
                  <Button
                    variant="outlined"
                    component="label"
                    fullWidth
                    sx={{ mt: 2, mb: 2 }}
                  >
                    Upload ID Card Photo
                    <input
                      type="file"
                      accept="image/png, image/jpeg, image/jpg"
                      hidden
                      onChange={handleFileChange}
                      required
                    />
                  </Button>
                  
                  {idCardPreview && (
                    <Box sx={{ mt: 2, textAlign: 'center' }}>
                      <img 
                        src={idCardPreview} 
                        alt="ID Card Preview" 
                        style={{ maxWidth: '100%', maxHeight: '200px', borderRadius: '8px' }} 
                      />
                    </Box>
                  )}
                </Grid>
                
                <Grid item xs={12}>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    By submitting this form, you agree to the terms and conditions of BRACU EUREKA. 
                    Your account will be pending until an administrator approves it.
                  </Typography>
                </Grid>
              </Grid>
              
              <Button
                variant="contained"
                color="secondary"
                type="submit"
                disabled={loading}
                fullWidth
                sx={{ 
                  py: 1.5, 
                  mt: 3,
                  backgroundColor: '#7b1fa2',
                  '&:hover': { 
                    backgroundColor: '#6a1b9a'
                  },
                  borderRadius: '8px'
                }}
              >
                {loading ? (
                  <CircularProgress size={24} color="inherit" />
                ) : (
                  'Submit Registration'
                )}
              </Button>
            </Box>
          </Box>
        )}
        
        <Box sx={{ mt: 3, width: '100%', textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            Already have an account?{' '}
            <MuiLink component={Link} to="/login" color="primary">
              Login here
            </MuiLink>
          </Typography>
        </Box>
      </Paper>
    </Container>
  );
};

export default Register; 